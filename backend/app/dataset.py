"""Synthetic Razorpay-style merchant dataset.

We generate a realistic mix of successful and failed payments with enough
per-customer signal (history, preferred method, risk) for the recovery agent
to make non-trivial decisions. The generator is seeded so the demo is
reproducible: the same seed always yields the same batch and therefore the
same headline "money recovered" number.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Dict, List

from .models import FailureCategory, Payment, PaymentStatus

METHODS = ["upi", "card", "netbanking", "wallet"]

# Failure codes grouped by the category they most naturally map to. The agent
# does NOT get the category for free — it re-derives it — but we keep the
# mapping here so the synthetic data is internally consistent.
FAILURE_CODES: Dict[FailureCategory, List[str]] = {
    FailureCategory.TEMPORARY: ["bank_timeout", "gateway_timeout", "network_error", "bank_error_window"],
    FailureCategory.CUSTOMER_ACTION: ["insufficient_funds", "authentication_abandoned", "otp_not_entered"],
    FailureCategory.METHOD_ISSUE: ["card_declined", "card_expired", "invalid_card", "auth_failure"],
    FailureCategory.SUBSCRIPTION: ["mandate_revoked", "mandate_expired", "recurring_declined"],
    FailureCategory.HIGH_RISK: ["risk_blocked", "velocity_exceeded", "suspicious_activity"],
    FailureCategory.UNKNOWN: ["unknown_error", "unspecified"],
}

# How the raw failure population is distributed. Mirrors the brief's batch
# breakdown so the demo numbers feel realistic.
CATEGORY_WEIGHTS = {
    FailureCategory.TEMPORARY: 0.34,
    FailureCategory.CUSTOMER_ACTION: 0.25,
    FailureCategory.METHOD_ISSUE: 0.20,
    FailureCategory.SUBSCRIPTION: 0.11,
    FailureCategory.UNKNOWN: 0.06,
    FailureCategory.HIGH_RISK: 0.04,
}


def _weighted_category(rng: random.Random) -> FailureCategory:
    cats, weights = zip(*CATEGORY_WEIGHTS.items())
    return rng.choices(cats, weights=weights, k=1)[0]


def _amount_for(rng: random.Random) -> float:
    """Realistic long-tail of amounts: mostly small, a few large."""
    bucket = rng.random()
    if bucket < 0.55:
        return float(rng.choice([199, 299, 499, 599, 899, 999]))
    if bucket < 0.85:
        return float(rng.choice([1499, 2999, 4999, 7500, 9999]))
    if bucket < 0.97:
        return float(rng.choice([12999, 19999, 24999, 34999]))
    return float(rng.choice([54999, 75000, 99999, 125000]))


def generate_dataset(n_payments: int = 1000, seed: int = 42) -> List[Payment]:
    rng = random.Random(seed)
    now = datetime(2026, 9, 4, 10, 0, 0)
    payments: List[Payment] = []

    # Build a stable pool of customers with their own history + preferences.
    n_customers = max(50, n_payments // 6)
    customers = []
    for i in range(n_customers):
        prev_success = rng.randint(0, 12)
        customers.append(
            {
                "id": f"CUST-{1000 + i}",
                "prev_success": prev_success,
                "prev_failure": rng.randint(0, 4),
                "preferred": rng.choices(METHODS, weights=[0.5, 0.3, 0.12, 0.08])[0],
                # New customers (few successes) carry a touch more inherent risk.
                "base_risk": max(0.0, 0.25 - prev_success * 0.02) + rng.random() * 0.1,
            }
        )

    for i in range(n_payments):
        cust = rng.choice(customers)
        amount = _amount_for(rng)
        method = cust["preferred"] if rng.random() < 0.7 else rng.choice(METHODS)
        ts = now - timedelta(minutes=rng.randint(0, 60 * 72))

        # ~15% of attempts fail overall.
        failed = rng.random() < 0.15
        if not failed:
            payments.append(
                Payment(
                    payment_id=f"RZP-{10000 + i}",
                    customer_id=cust["id"],
                    amount=amount,
                    timestamp=ts.isoformat(),
                    payment_method=method,
                    status=PaymentStatus.SUCCESS,
                    previous_successes=cust["prev_success"],
                    previous_failures=cust["prev_failure"],
                    preferred_method=cust["preferred"],
                    risk_score=round(cust["base_risk"], 3),
                )
            )
            continue

        category = _weighted_category(rng)
        code = rng.choice(FAILURE_CODES[category])
        retry_count = rng.choices([0, 1, 2, 3], weights=[0.55, 0.25, 0.13, 0.07])[0]
        reminder_count = rng.choices([0, 1, 2], weights=[0.7, 0.2, 0.1])[0]
        hours_since = round(rng.uniform(0.1, 96.0), 1)

        risk = cust["base_risk"]
        if category == FailureCategory.HIGH_RISK:
            risk = max(risk, rng.uniform(0.7, 0.95))
        risk = min(0.99, round(risk + rng.random() * 0.05, 3))

        subscription_id = None
        days_overdue = 0
        if category == FailureCategory.SUBSCRIPTION:
            subscription_id = f"SUB-{2000 + rng.randint(0, 400)}"
            days_overdue = rng.randint(0, 20)

        payments.append(
            Payment(
                payment_id=f"RZP-{10000 + i}",
                customer_id=cust["id"],
                amount=amount,
                timestamp=ts.isoformat(),
                payment_method=method,
                status=PaymentStatus.FAILED,
                failure_code=code,
                failure_category=None,  # agent must re-derive this
                device=rng.choice(["android", "ios", "web"]),
                previous_successes=cust["prev_success"],
                previous_failures=cust["prev_failure"],
                preferred_method=cust["preferred"],
                retry_count=retry_count,
                reminder_count=reminder_count,
                first_failure_ts=(ts - timedelta(hours=hours_since)).isoformat(),
                hours_since_first_failure=hours_since,
                subscription_id=subscription_id,
                days_overdue=days_overdue,
                risk_score=risk,
            )
        )

    return payments


# Map any failure code back to its category (used by the diagnosis agent as one
# of several signals — not as a shortcut, since real failure codes are noisy).
CODE_TO_CATEGORY: Dict[str, FailureCategory] = {
    code: cat for cat, codes in FAILURE_CODES.items() for code in codes
}
