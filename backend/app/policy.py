"""Deterministic recovery policy engine.

This layer contains NO AI. It is the safety boundary around the agent's
judgment: hard limits on retries, recovery windows, reminders, high-value
approvals and risk. Every check is a plain, auditable rule. The agent may
*want* to retry a payment, but the policy engine decides whether that action
is actually permitted — and can force a terminal STOP or ESCALATE.

Keeping this separate from the reasoning layer is a deliberate design choice:
financial safety must be predictable, not probabilistic.
"""
from __future__ import annotations

from .models import (
    ActionType,
    Decision,
    Payment,
    PolicyCheck,
    PolicyResult,
)

# --------------------------------------------------------------------------- #
# Tunable, deterministic limits. These are business rules, not model outputs.
# --------------------------------------------------------------------------- #
MAX_RETRIES = 3
MAX_RECOVERY_WINDOW_HOURS = 72
MAX_REMINDERS = 2
HIGH_VALUE_THRESHOLD = 50_000        # ₹ — requires human approval
SUSPICIOUS_RISK_THRESHOLD = 0.7      # >= this = no automatic recovery


def evaluate(payment: Payment, decision: Decision) -> PolicyResult:
    """Validate a proposed action against the policy. Pure function."""
    checks: list[PolicyCheck] = []
    terminal: ActionType | None = None
    requires_approval = False

    # 1) Suspicious / high-risk transactions are never auto-recovered.
    suspicious = payment.risk_score >= SUSPICIOUS_RISK_THRESHOLD
    checks.append(
        PolicyCheck(
            name="risk_screen",
            passed=not suspicious,
            detail=(
                f"risk_score={payment.risk_score:.2f} "
                f"(threshold {SUSPICIOUS_RISK_THRESHOLD})"
            ),
        )
    )
    if suspicious:
        terminal = ActionType.ESCALATE_TO_HUMAN

    # 2) Retry ceiling. Only relevant to retry-style actions.
    retry_ok = payment.retry_count < MAX_RETRIES
    checks.append(
        PolicyCheck(
            name="retry_limit",
            passed=retry_ok,
            detail=f"retry_count={payment.retry_count} (max {MAX_RETRIES})",
        )
    )
    if not retry_ok and decision.action in (
        ActionType.RETRY_PAYMENT,
        ActionType.SUGGEST_ALTERNATE_METHOD,
    ):
        terminal = terminal or ActionType.STOP_RECOVERY

    # 3) Recovery window. Past the window we stop chasing.
    window_ok = payment.hours_since_first_failure <= MAX_RECOVERY_WINDOW_HOURS
    checks.append(
        PolicyCheck(
            name="recovery_window",
            passed=window_ok,
            detail=(
                f"{payment.hours_since_first_failure:.1f}h since first failure "
                f"(max {MAX_RECOVERY_WINDOW_HOURS}h)"
            ),
        )
    )
    if not window_ok:
        terminal = terminal or ActionType.STOP_RECOVERY

    # 4) Reminder ceiling. Only relevant to reminder actions.
    reminder_ok = payment.reminder_count < MAX_REMINDERS
    checks.append(
        PolicyCheck(
            name="reminder_limit",
            passed=reminder_ok,
            detail=f"reminder_count={payment.reminder_count} (max {MAX_REMINDERS})",
        )
    )
    if not reminder_ok and decision.action == ActionType.SEND_REMINDER:
        terminal = terminal or ActionType.STOP_RECOVERY

    # 5) High-value approval gate.
    high_value = payment.amount >= HIGH_VALUE_THRESHOLD
    checks.append(
        PolicyCheck(
            name="high_value_approval",
            passed=not high_value,
            detail=f"amount=₹{payment.amount:,.0f} (threshold ₹{HIGH_VALUE_THRESHOLD:,})",
        )
    )
    if high_value:
        requires_approval = True

    # An action is allowed only if there is no terminal override, it does not
    # require (missing) human approval, and it is not itself a terminal action.
    agent_terminal = decision.action in (
        ActionType.ESCALATE_TO_HUMAN,
        ActionType.STOP_RECOVERY,
    )
    allowed = terminal is None and not requires_approval and not agent_terminal

    return PolicyResult(
        allowed=allowed,
        checks=checks,
        requires_human_approval=requires_approval,
        terminal_action=terminal,
    )
