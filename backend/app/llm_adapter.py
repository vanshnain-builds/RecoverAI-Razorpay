"""Optional LLM adapter for the recovery agent.

This module is only imported when RECOVERAI_USE_LLM=1 and a key is present.
It shows exactly where a real model call goes and enforces that the model's
output is coerced back into our strict Pydantic shapes. The prompts below are
the ones the agent would use.

We deliberately keep the model responsible ONLY for reasoning (diagnosis +
action choice + explanation). It never sees or sets policy limits or recovered
amounts — those stay deterministic. If the call fails or returns malformed
JSON, agent.py falls back to the simulated engine.

To keep the base project dependency-free and always-runnable, no SDK is
imported at module load. Wire your client of choice inside the functions.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict

from .models import ActionType, Decision, Diagnosis, Evidence, FailureCategory, Payment

DIAGNOSIS_SYSTEM_PROMPT = """\
You are a payment-failure diagnosis expert for an Indian payments platform.
Given one failed payment and the customer's history, classify WHY it failed.

Return STRICT JSON with keys:
  category: one of [temporary_failure, customer_action, payment_method_issue,
            subscription_failure, high_risk, unknown]
  human_reason: one short sentence
  confidence: number 0..1
  evidence: array of {text: string, supports_recovery: boolean}

Rules:
- Base confidence on corroborating signals (history, risk, method), not just
  the failure code.
- If risk indicators are high, category MUST be high_risk.
- Do NOT recommend an action here; only diagnose.
"""

DECISION_SYSTEM_PROMPT = """\
You are a revenue-recovery strategist. Given a diagnosed failed payment, choose
the single best recovery ACTION to maximise expected recovered revenue safely.

Available actions:
  retry_payment, send_payment_link, suggest_alternate_method, send_reminder,
  offer_incentive, escalate_to_human, stop_recovery

Return STRICT JSON with keys:
  action: one of the actions above
  recovery_probability: number 0..1
  rationale: array of short strings explaining the choice

Rules:
- high_risk cases -> escalate_to_human.
- Prefer the lowest-friction action with the best odds.
- You do NOT enforce retry/window/approval limits; a separate policy engine does.
"""


def _client_call(system: str, user: str) -> Dict[str, Any]:
    """Route to whichever provider is configured. Raises on any problem so the
    caller can fall back to the simulated engine."""
    if os.getenv("ANTHROPIC_API_KEY"):
        import anthropic  # type: ignore

        client = anthropic.Anthropic()
        model = os.getenv("RECOVERAI_LLM_MODEL", "claude-3-5-sonnet-latest")
        resp = client.messages.create(
            model=model,
            max_tokens=600,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = resp.content[0].text
    elif os.getenv("OPENAI_API_KEY"):
        from openai import OpenAI  # type: ignore

        client = OpenAI()
        model = os.getenv("RECOVERAI_LLM_MODEL", "gpt-4o-mini")
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content
    else:
        raise RuntimeError("No LLM provider configured")

    return json.loads(text)


def _payment_brief(p: Payment) -> str:
    return json.dumps(
        {
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
    return Diagnosis(
        payment_id=p.payment_id,
        category=FailureCategory(data["category"]),
        human_reason=data["human_reason"],
        confidence=float(data["confidence"]),
        evidence=[Evidence(**e) for e in data.get("evidence", [])],
        source="llm",
    )


def llm_decide(p: Payment, d: Diagnosis) -> Decision:
    user = json.dumps({"payment": json.loads(_payment_brief(p)),
                       "diagnosis": {"category": d.category.value,
                                     "confidence": d.confidence}})
    data = _client_call(DECISION_SYSTEM_PROMPT, user)
    prob = float(data["recovery_probability"])
    expected = round(p.amount * prob, 2)
    return Decision(
        payment_id=p.payment_id,
        action=ActionType(data["action"]),
        recovery_probability=prob,
        expected_recovery_value=expected,
        recovery_priority=round(expected * (1 - p.risk_score * 0.5), 2),
        rationale=list(data.get("rationale", [])),
        source="llm",
    )
