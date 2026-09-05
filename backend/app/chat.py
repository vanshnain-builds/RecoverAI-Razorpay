"""Conversational interface to the engine.

This is deliberately thin: the chat is just a natural-language *front door* to
the same engine methods the UI calls. It is intent-matched, not a free-form
chatbot, which keeps behaviour predictable for the demo. (If the LLM is
enabled, this is the natural place to swap in intent classification.)
"""
from __future__ import annotations

import re
from typing import Dict

from .engine import RecoveryEngine


def handle(engine: RecoveryEngine, message: str) -> Dict:
    text = message.lower().strip()
    # Ensure reasoning has run so recoverable/expected figures are populated.
    engine.diagnose_all()
    m = engine.metrics()

    def rupees(x: float) -> str:
        return f"₹{x:,.0f}"

    # Intent: run recovery (check first — phrases like "recover it" also
    # contain the substring "recover" used by the recoverable-amount intent).
    if re.search(r"(recover it|start recovery|run recovery|recover eligible|recover all|do it)", text):
        result = engine.recover_batch()
        return {
            "reply": (
                f"Done. Executed {result['actions_executed']} recovery actions and "
                f"recovered {rupees(result['recovered_amount'])}. "
                f"{rupees(result['escalated_amount'])} was escalated for human review and "
                f"{rupees(result['abandoned_amount'])} was stopped by policy. "
                "Transactions above the high-value threshold and high-risk cases were held for approval."
            ),
            "data": result,
        }

    # Intent: recovered so far
    if "recovered" in text:
        return {
            "reply": (
                f"{rupees(m['recovered_amount'])} recovered so far across "
                f"{m['recovered_count']} payments (recovery rate {m['recovery_rate']*100:.1f}%)."
            ),
            "data": m,
        }

    # Intent: how much lost / at risk
    if re.search(r"(lost|at risk|losing|leak|fail)", text):
        return {
            "reply": (
                f"{rupees(m['revenue_at_risk'])} is currently at risk across "
                f"{m['failed_count']} failed payments."
            ),
            "data": m,
        }

    # Intent: how much recoverable
    if re.search(r"(recover(able)?|can we get|how much can)", text):
        return {
            "reply": (
                f"About {rupees(m['recoverable_total'])} has recovery probability "
                f"above threshold. {rupees(m['recovered_amount'])} has already been recovered."
            ),
            "data": m,
        }

    return {
        "reply": (
            "I can tell you how much revenue is at risk, how much is recoverable, "
            "recover eligible payments, or report what's been recovered. Try "
            "\"how much is at risk?\" or \"start recovery\"."
        ),
        "data": m,
    }
