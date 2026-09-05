"""Recovery Agent — the reasoning layer.

Responsibilities (the "DETECT -> DIAGNOSE -> PREDICT -> DECIDE" stages):
  * diagnose()  — why did this payment fail? (category + confidence + evidence)
  * decide()    — what is the highest expected-value safe action?

By default this runs a *simulated* reasoning engine: transparent, deterministic
heuristics that produce the same shape of output an LLM would (confidence,
evidence, rationale). This guarantees the demo always runs with no API key and
no network.

If RECOVERAI_USE_LLM=1 and an API key is present, diagnose()/decide() route
through an LLM adapter instead, falling back to the simulated engine on any
error. This is the "hybrid" design: simulated by default, LLM optional.

Note on AI judgment: this module reasons and explains. It does NOT enforce
safety limits or compute the final recovered amount — those are deterministic
and live in policy.py / executor.py. That separation is intentional.
"""
from __future__ import annotations

import os
from typing import List

from .dataset import CODE_TO_CATEGORY
from .models import (
    ActionType,
    Decision,
    Diagnosis,
    Evidence,
    FailureCategory,
    Payment,
)

# --------------------------------------------------------------------------- #
# Base recovery odds per failure category (before customer-specific signal).
# --------------------------------------------------------------------------- #
BASE_RECOVERY_ODDS = {
    FailureCategory.TEMPORARY: 0.82,
    FailureCategory.CUSTOMER_ACTION: 0.55,
    FailureCategory.METHOD_ISSUE: 0.60,
    FailureCategory.SUBSCRIPTION: 0.50,
    FailureCategory.UNKNOWN: 0.30,
    FailureCategory.HIGH_RISK: 0.10,
}


# --------------------------------------------------------------------------- #
# Simulated reasoning engine
# --------------------------------------------------------------------------- #
def _diagnose_simulated(p: Payment) -> Diagnosis:
    # Primary signal: the failure code. But we corroborate with independent
    # signals so the confidence reflects real evidence, not just a lookup.
    category = CODE_TO_CATEGORY.get(p.failure_code or "", FailureCategory.UNKNOWN)

    evidence: List[Evidence] = []
    confidence = 0.55  # start uncertain; evidence raises/lowers it

    if p.previous_successes >= 3:
        evidence.append(Evidence(
            text=f"Customer has {p.previous_successes} previous successful payments",
            supports_recovery=True))
        confidence += 0.12
    if p.previous_successes == 0:
        evidence.append(Evidence(
            text="First-time customer — limited payment history",
            supports_recovery=False))
        confidence -= 0.05

    if p.risk_score >= 0.7:
        category = FailureCategory.HIGH_RISK
        evidence.append(Evidence(
            text=f"Elevated risk score ({p.risk_score:.2f}) — fraud indicators present",
            supports_recovery=False))
        confidence = max(confidence, 0.8)
    elif p.risk_score < 0.2:
        evidence.append(Evidence(
            text="No unusual account activity detected",
            supports_recovery=True))
        confidence += 0.05

    if category == FailureCategory.TEMPORARY:
        evidence.append(Evidence(
            text="Failure occurred during a transient bank/network error window",
            supports_recovery=True))
        confidence += 0.15
    if category == FailureCategory.SUBSCRIPTION and p.subscription_id:
        evidence.append(Evidence(
            text=f"Recurring mandate {p.subscription_id}, {p.days_overdue} days overdue",
            supports_recovery=True))
    if category == FailureCategory.METHOD_ISSUE and p.preferred_method and p.preferred_method != p.payment_method:
        evidence.append(Evidence(
            text=f"Customer usually pays via {p.preferred_method.upper()}, not {p.payment_method.upper()}",
            supports_recovery=True))
        confidence += 0.08

    confidence = round(min(0.97, max(0.4, confidence)), 2)

    reasons = {
        FailureCategory.TEMPORARY: "Temporary bank/payment network failure",
        FailureCategory.CUSTOMER_ACTION: "Payment needs a customer action to complete",
        FailureCategory.METHOD_ISSUE: "Problem with the specific payment instrument used",
        FailureCategory.SUBSCRIPTION: "Recurring mandate failed to charge",
        FailureCategory.HIGH_RISK: "Transaction flagged with high-risk / fraud indicators",
        FailureCategory.UNKNOWN: "Failure cause could not be determined confidently",
    }

    return Diagnosis(
        payment_id=p.payment_id,
        category=category,
        human_reason=reasons[category],
        confidence=confidence,
        evidence=evidence,
        source="simulated",
    )


def _recovery_probability(p: Payment, d: Diagnosis) -> float:
    odds = BASE_RECOVERY_ODDS[d.category]
    # Customer history nudges odds up; repeated failures / retries nudge down.
    odds += min(0.12, p.previous_successes * 0.015)
    odds -= min(0.20, p.retry_count * 0.07)
    odds -= min(0.10, p.previous_failures * 0.03)
    if p.risk_score >= 0.7:
        odds = min(odds, 0.12)
    return round(min(0.97, max(0.02, odds)), 2)


def _choose_action(p: Payment, d: Diagnosis, prob: float) -> tuple[ActionType, List[str]]:
    """Pick the highest-expected-value *reasonable* action for the case.

    The policy engine still gets the final say on whether it's permitted; here
    we choose what the agent believes is best.
    """
    r: List[str] = []

    if d.category == FailureCategory.HIGH_RISK:
        r.append("High-risk indicators present; automatic recovery is unsafe")
        return ActionType.ESCALATE_TO_HUMAN, r

    if p.retry_count >= 3:
        r.append("Retry attempts exhausted; further automated retries won't help")
        return ActionType.STOP_RECOVERY, r

    if d.category == FailureCategory.TEMPORARY:
        if p.preferred_method and p.preferred_method != p.payment_method:
            r.append(f"Customer prefers {p.preferred_method.upper()} and it succeeded before")
            r.append("Failure is transient, so an immediate retry has high odds")
            return ActionType.SUGGEST_ALTERNATE_METHOD, r
        r.append("Transient failure with strong customer history favours a direct retry")
        return ActionType.RETRY_PAYMENT, r

    if d.category == FailureCategory.METHOD_ISSUE:
        r.append("Instrument-level failure; steering to an alternate method avoids repeat declines")
        return ActionType.SUGGEST_ALTERNATE_METHOD, r

    if d.category == FailureCategory.CUSTOMER_ACTION:
        if p.amount >= 10_000:
            r.append("Higher-value, customer-action failure; a payment link is the cleanest path")
            return ActionType.SEND_PAYMENT_LINK, r
        r.append("Customer needs to act; a reminder is the lowest-friction nudge")
        return ActionType.SEND_REMINDER, r

    if d.category == FailureCategory.SUBSCRIPTION:
        r.append("Recurring mandate failure; a staged retry sequence recovers most of these")
        return ActionType.RETRY_PAYMENT, r

    # Unknown / low confidence
    if prob < 0.35:
        r.append("Low recovery probability and unclear cause; not worth an automated attempt")
        return ActionType.STOP_RECOVERY, r
    r.append("Cause unclear but odds acceptable; a payment link lets the customer self-serve")
    return ActionType.SEND_PAYMENT_LINK, r


def _decide_simulated(p: Payment, d: Diagnosis) -> Decision:
    prob = _recovery_probability(p, d)
    action, rationale = _choose_action(p, d, prob)

    # Expected recovery value = amount * probability. This is the core
    # optimisation signal used to prioritise the queue.
    expected = round(p.amount * prob, 2)

    # Recovery priority blends expected value with a small penalty for risk and
    # for actions that consume more operational effort.
    effort_penalty = {
        ActionType.RETRY_PAYMENT: 0.0,
        ActionType.SUGGEST_ALTERNATE_METHOD: 0.02,
        ActionType.SEND_PAYMENT_LINK: 0.05,
        ActionType.SEND_REMINDER: 0.05,
        ActionType.OFFER_INCENTIVE: 0.15,
        ActionType.ESCALATE_TO_HUMAN: 0.0,
        ActionType.STOP_RECOVERY: 0.0,
    }.get(action, 0.05)
    priority = round(expected * (1 - effort_penalty) * (1 - p.risk_score * 0.5), 2)

    return Decision(
        payment_id=p.payment_id,
        action=action,
        recovery_probability=prob,
        expected_recovery_value=expected,
        recovery_priority=priority,
        rationale=rationale,
        source="simulated",
    )


# --------------------------------------------------------------------------- #
# Optional LLM adapter (hybrid). Simulated engine is always the fallback.
# --------------------------------------------------------------------------- #
def _llm_enabled() -> bool:
    return os.getenv("RECOVERAI_USE_LLM", "0") == "1" and bool(
        os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    )


def _diagnose_llm(p: Payment) -> Diagnosis:
    """Placeholder adapter. Wire a real client here.

    We keep the interface identical to the simulated engine so callers never
    branch. Any exception bubbles up to diagnose(), which falls back.
    """
    from .llm_adapter import llm_diagnose  # local import keeps base install light
    return llm_diagnose(p)


def _decide_llm(p: Payment, d: Diagnosis) -> Decision:
    from .llm_adapter import llm_decide
    return llm_decide(p, d)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def diagnose(p: Payment) -> Diagnosis:
    if _llm_enabled():
        try:
            return _diagnose_llm(p)
        except Exception:
            pass  # fall back silently to the always-available engine
    return _diagnose_simulated(p)


def decide(p: Payment, d: Diagnosis) -> Decision:
    if _llm_enabled():
        try:
            return _decide_llm(p, d)
        except Exception:
            pass
    return _decide_simulated(p, d)
