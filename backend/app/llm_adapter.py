"""NVIDIA Nemotron 3.5 Lightning adapter for RecoverAI.

The LLM is used for reasoning only: diagnosis, recovery-action selection and
explanations. Deterministic policy/execution code remains responsible for
safety limits, recovered amounts and actual payment execution.

Provider: NVIDIA hosted NIM API
Endpoint: https://integrate.api.nvidia.com/v1/chat/completions
Model: nvidia/nemotron-3.5-lightning-30b-a3b

The adapter uses the existing `requests` dependency, so no extra SDK is needed.
If the NVIDIA call fails or returns malformed output, the recovery agent falls
back to its deterministic reasoning engine.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict

import requests

from .models import ActionType, Decision, Diagnosis, Evidence, FailureCategory, Payment

NVIDIA_API_URL = os.getenv(
    "NVIDIA_API_URL", "https://integrate.api.nvidia.com/v1/chat/completions"
).rstrip("/")
DEFAULT_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"

DIAGNOSIS_SYSTEM_PROMPT = """\
You are RecoverAI's payment-failure diagnosis expert for an Indian payments
platform. Analyze the supplied failed payment and customer history.

Return ONLY valid JSON. Do not use markdown fences and do not add commentary.
Schema:
{
  "category": "temporary_failure|customer_action|payment_method_issue|subscription_failure|high_risk|unknown",
  "human_reason": "one short sentence",
  "confidence": 0.0,
  "evidence": [
    {"text": "short evidence statement", "supports_recovery": true}
  ]
}

Rules:
- Base the diagnosis on multiple signals when available, not only the failure code.
- If risk_score >= 0.70, category MUST be high_risk.
- Do not recommend a recovery action in this response.
- confidence must be between 0 and 1.
- Keep evidence concise and grounded in the supplied data.
"""

DECISION_SYSTEM_PROMPT = """\
You are RecoverAI's revenue-recovery strategist. Given a diagnosed failed
payment, select the single best recovery action to maximize expected recovered
revenue while minimizing unnecessary customer friction.

Return ONLY valid JSON. Do not use markdown fences and do not add commentary.
Schema:
{
  "action": "retry_payment|send_payment_link|suggest_alternate_method|send_reminder|offer_incentive|escalate_to_human|stop_recovery",
  "recovery_probability": 0.0,
  "rationale": ["short reason", "short reason"]
}

Rules:
- high_risk cases MUST use escalate_to_human.
- Prefer the lowest-friction action with the best recovery odds.
- Do not enforce retry limits, approval limits or policy thresholds; those are
  handled by RecoverAI's deterministic policy engine.
- recovery_probability must be between 0 and 1.
"""


def _extract_json(text: str) -> Dict[str, Any]:
    """Parse JSON even if a model accidentally wraps it in a code fence."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def _client_call(system: str, user: str) -> Dict[str, Any]:
    """Call NVIDIA's hosted OpenAI-compatible NIM endpoint."""
    api_key = os.getenv("NVIDIA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("NVIDIA_API_KEY is not configured")

    model = os.getenv("RECOVERAI_LLM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    response = requests.post(
        NVIDIA_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
            "top_p": 0.7,
            "max_tokens": 800,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
        },
        timeout=45,
    )
    response.raise_for_status()

    payload = response.json()
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("NVIDIA returned no choices")

    message = choices[0].get("message") or {}
    text = message.get("content")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("NVIDIA returned an empty response")

    return _extract_json(text)


def _payment_brief(p: Payment) -> str:
    return json.dumps(
        {
            "payment_id": p.payment_id,
            "amount": p.amount,
            "payment_method": p.payment_method,
            "failure_code": p.failure_code,
            "previous_successes": p.previous_successes,
            "previous_failures": p.previous_failures,
            "preferred_method": p.preferred_method,
            "retry_count": p.retry_count,
            "risk_score": p.risk_score,
            "days_overdue": p.days_overdue,
            "subscription_id": p.subscription_id,
        }
    )


def llm_diagnose(p: Payment) -> Diagnosis:
    data = _client_call(DIAGNOSIS_SYSTEM_PROMPT, _payment_brief(p))
    category = FailureCategory(data["category"])
    evidence = [
        Evidence(**e)
        for e in data.get("evidence", [])
        if isinstance(e, dict) and "text" in e
    ]
    return Diagnosis(
        payment_id=p.payment_id,
        category=category,
        human_reason=str(data["human_reason"]),
        confidence=max(0.0, min(1.0, float(data["confidence"]))),
        evidence=evidence,
        source="llm:nemotron-3.5-lightning",
    )


def llm_decide(p: Payment, d: Diagnosis) -> Decision:
    user = json.dumps(
        {
            "payment": json.loads(_payment_brief(p)),
            "diagnosis": {
                "category": d.category.value,
                "human_reason": d.human_reason,
                "confidence": d.confidence,
                "evidence": [e.model_dump() for e in d.evidence],
            },
        }
    )
    data = _client_call(DECISION_SYSTEM_PROMPT, user)
    prob = max(0.0, min(1.0, float(data["recovery_probability"])))
    expected = round(p.amount * prob, 2)

    return Decision(
        payment_id=p.payment_id,
        action=ActionType(data["action"]),
        recovery_probability=prob,
        expected_recovery_value=expected,
        recovery_priority=round(expected * (1 - p.risk_score * 0.5), 2),
        rationale=[str(x) for x in data.get("rationale", [])],
        source="llm:nemotron-3.5-lightning",
    )
