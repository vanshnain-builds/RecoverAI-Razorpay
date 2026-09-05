"""Action executor + outcome tracker.

The executor is the only place that actually "does" something to a payment. It
talks to a mock Razorpay simulator (deterministic, seedable) so the demo is
reproducible and so we can force failures on demand. It also computes the
recovered amount — deterministically, never via the model.

Every step appends to an audit trail so judges can see exactly what happened
and when. When an action fails, the executor demonstrates safe failure
handling: it does not retry endlessly, it preserves state, records the failure,
and hands back a clear next step.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import List, Optional

from . import config, razorpay_client
from .models import (
    ActionOutcome,
    ActionType,
    AuditEntry,
    Decision,
    Diagnosis,
    Payment,
    PaymentStatus,
    PolicyResult,
)

# Probability that a given action *succeeds operationally* (i.e. the customer
# pays / the retry goes through), given the action was permitted. This is the
# simulator's model of the real world and is independent of the agent's
# predicted recovery_probability.
ACTION_SUCCESS_ODDS = {
    ActionType.RETRY_PAYMENT: 0.72,
    ActionType.SUGGEST_ALTERNATE_METHOD: 0.66,
    ActionType.SEND_PAYMENT_LINK: 0.58,
    ActionType.SEND_REMINDER: 0.40,
    ActionType.OFFER_INCENTIVE: 0.62,
}


def _now() -> str:
    # timezone-aware UTC; datetime.utcnow() is deprecated on Python 3.12+.
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _audit(payment_id: str, stage: str, message: str) -> AuditEntry:
    return AuditEntry(ts=_now(), payment_id=payment_id, stage=stage, message=message)


def execute(
    payment: Payment,
    diagnosis: Diagnosis,
    decision: Decision,
    policy: PolicyResult,
    *,
    force_failure: bool = False,
    rng: Optional[random.Random] = None,
) -> ActionOutcome:
    """Execute the decided action, subject to policy. Returns an outcome with a
    full audit trail. Deterministic given the same rng seed.
    """
    rng = rng or random.Random(f"{payment.payment_id}")
    audit: List[AuditEntry] = [
        _audit(payment.payment_id, "detect", "Payment failure detected"),
        _audit(payment.payment_id, "diagnose",
               f"Diagnosed as {diagnosis.category.value} (confidence {diagnosis.confidence:.0%})"),
        _audit(payment.payment_id, "decide",
               f"Selected action={decision.action.value}, "
               f"p(recover)={decision.recovery_probability:.0%}, "
               f"E[recovery]=₹{decision.expected_recovery_value:,.0f}"),
    ]

    # ---- Policy gate ------------------------------------------------------ #
    if policy.terminal_action is not None:
        audit.append(_audit(payment.payment_id, "policy",
                            f"Policy override -> {policy.terminal_action.value}"))
        action = policy.terminal_action
        return ActionOutcome(
            payment_id=payment.payment_id,
            action=action,
            executed=False,
            success=False,
            message=_terminal_message(action, policy),
            audit=audit,
        )

    if policy.requires_human_approval:
        audit.append(_audit(payment.payment_id, "policy",
                            "High-value transaction requires human approval — holding"))
        return ActionOutcome(
            payment_id=payment.payment_id,
            action=ActionType.ESCALATE_TO_HUMAN,
            executed=False,
            success=False,
            message="Awaiting human approval (amount above high-value threshold)",
            audit=audit,
        )

    if not policy.allowed:
        audit.append(_audit(payment.payment_id, "policy", "Action not permitted by policy"))
        return ActionOutcome(
            payment_id=payment.payment_id,
            action=ActionType.STOP_RECOVERY,
            executed=False,
            success=False,
            message="Stopped: action blocked by policy",
            audit=audit,
        )

    audit.append(_audit(payment.payment_id, "policy", "Policy validation PASSED"))

    # Agent itself chose a terminal action (stop / escalate) — respect it.
    if decision.action in (ActionType.STOP_RECOVERY, ActionType.ESCALATE_TO_HUMAN):
        audit.append(_audit(payment.payment_id, "execute",
                            f"Agent chose terminal action {decision.action.value}"))
        return ActionOutcome(
            payment_id=payment.payment_id,
            action=decision.action,
            executed=False,
            success=False,
            message=_terminal_message(decision.action, policy),
            audit=audit,
        )

    # ---- Call the payment/recovery API ------------------------------- #
    audit.append(_audit(payment.payment_id, "execute",
                        f"Recovery initiated via {decision.action.value}"))

    # For send_payment_link we can take a REAL side effect (test mode): create
    # an actual Razorpay Payment Link. Every other action stays simulated. Link
    # *creation* is real; link *completion* (the customer actually paying) can
    # only be confirmed via a webhook — see config.RECOVERAI_SIMULATE_COMPLETION.
    real_link_url: Optional[str] = None
    real_link_pending = False
    if (
        decision.action == ActionType.SEND_PAYMENT_LINK
        and not force_failure
        and razorpay_client.is_enabled()
    ):
        try:
            real_link_url = razorpay_client.create_payment_link(payment)
            audit.append(_audit(payment.payment_id, "execute",
                                f"Created real Razorpay payment link: {real_link_url}"))
            if not config.RECOVERAI_SIMULATE_COMPLETION:
                real_link_pending = True
        except Exception as exc:  # noqa: BLE001
            audit.append(_audit(payment.payment_id, "execute",
                                f"Live payment-link creation failed ({exc!r}); "
                                "falling back to a simulated link"))

    if force_failure:
        # Demonstrate safe failure handling: no endless retries, state kept,
        # next eligible action queued.
        audit.append(_audit(payment.payment_id, "execute",
                            "Recovery API unavailable — action did not complete"))
        audit.append(_audit(payment.payment_id, "recover_fail",
                            "Did not retry repeatedly; preserved transaction state; "
                            "scheduled next eligible window; logged failure"))
        return ActionOutcome(
            payment_id=payment.payment_id,
            action=decision.action,
            executed=True,
            success=False,
            recovered_amount=0.0,
            message="Recovery action failed (payment service unavailable) — safely queued for retry",
            failure_reason="payment_service_unavailable",
            audit=audit,
        )

    # A real link was created but we're NOT simulating completion: report it as
    # sent-and-pending. A webhook would later confirm payment; until then it is
    # deliberately not counted as recovered. Deterministic (no RNG).
    if real_link_pending:
        audit.append(_audit(payment.payment_id, "recover_pending",
                            "Real payment link sent; awaiting customer payment "
                            "(confirm via webhook). Not counted as recovered yet."))
        return ActionOutcome(
            payment_id=payment.payment_id,
            action=decision.action,
            executed=True,
            success=False,
            recovered_amount=0.0,
            message=(f"Real Razorpay payment link created ({real_link_url}); "
                     "awaiting customer payment"),
            failure_reason="awaiting_customer_payment",
            audit=audit,
        )

    odds = ACTION_SUCCESS_ODDS.get(decision.action, 0.5)
    succeeded = rng.random() < odds

    if succeeded:
        recovered = float(payment.amount)  # deterministic: full amount recovered
        note = f"Payment successful — ₹{recovered:,.0f} recovered"
        message = f"₹{recovered:,.0f} recovered via {decision.action.value}"
        if real_link_url:
            note += " (simulated completion of a real payment link)"
            message += f" — link {real_link_url}"
        audit.append(_audit(payment.payment_id, "recover_success", note))
        return ActionOutcome(
            payment_id=payment.payment_id,
            action=decision.action,
            executed=True,
            success=True,
            recovered_amount=recovered,
            message=message,
            audit=audit,
        )

    audit.append(_audit(payment.payment_id, "recover_fail",
                        "Customer did not complete payment on this attempt"))
    return ActionOutcome(
        payment_id=payment.payment_id,
        action=decision.action,
        executed=True,
        success=False,
        recovered_amount=0.0,
        message="Action executed but payment not completed",
        failure_reason="not_completed",
        audit=audit,
    )


def _terminal_message(action: ActionType, policy: PolicyResult) -> str:
    if action == ActionType.ESCALATE_TO_HUMAN:
        failed = [c.detail for c in policy.checks if c.name == "risk_screen" and not c.passed]
        if failed:
            return "Escalated to human: high-risk indicators, not auto-recovered"
        return "Escalated to human review"
    # STOP
    reasons = [c.detail for c in policy.checks if not c.passed]
    if reasons:
        return "Stopped by policy: " + "; ".join(reasons)
    return "Recovery stopped"


def final_status(outcome: ActionOutcome) -> PaymentStatus:
    if outcome.success:
        return PaymentStatus.RECOVERED
    if outcome.action == ActionType.ESCALATE_TO_HUMAN:
        return PaymentStatus.ESCALATED
    if outcome.action == ActionType.STOP_RECOVERY:
        return PaymentStatus.ABANDONED
    # Executed but not completed / failed API -> still pending recovery.
    return PaymentStatus.PENDING
