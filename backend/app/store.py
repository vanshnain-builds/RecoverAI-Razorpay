"""Supabase persistence — write-through via the PostgREST REST API.

We deliberately avoid the heavy `supabase` SDK (and native Postgres drivers) so
the dependency set stays wheel-only and Python 3.14-safe: this talks to
`{SUPABASE_URL}/rest/v1/<table>` with the service-role key using plain HTTP.

Design:
  * Disabled unless SUPABASE_URL + SUPABASE_SERVICE_KEY are set.
  * Every call is best-effort and wrapped — a persistence error is logged and
    swallowed so it can NEVER break the recovery loop or the demo.
  * The engine still runs in memory (fast, reproducible); we mirror state into
    Postgres. Tables/enums must already exist — run db/supabase_schema.sql once.
"""
from __future__ import annotations

import json
import sys
from typing import Dict, List

from . import config
from .models import Payment, RecoveryRecord

_last_error: str | None = None


def is_enabled() -> bool:
    return config.supabase_enabled()


def status() -> Dict:
    return {"enabled": is_enabled(), "last_error": _last_error}


def _headers(upsert: bool = False) -> Dict[str, str]:
    prefer = "return=minimal"
    if upsert:
        prefer += ",resolution=merge-duplicates"
    return {
        "apikey": config.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _write(table: str, rows: List[Dict], on_conflict: str | None = None) -> None:
    global _last_error
    if not rows:
        return
    try:
        import requests  # lazy import; only needed when persistence is on

        url = f"{config.SUPABASE_URL}/rest/v1/{table}"
        params = {"on_conflict": on_conflict} if on_conflict else None
        resp = requests.post(
            url,
            headers=_headers(upsert=bool(on_conflict)),
            params=params,
            data=json.dumps(rows, default=str),
            timeout=20,
        )
        if resp.status_code >= 300:
            _last_error = f"{table}: HTTP {resp.status_code} {resp.text[:200]}"
            print(f"[RecoverAI] Supabase write failed -> {_last_error}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        _last_error = f"{table}: {exc!r}"
        print(f"[RecoverAI] Supabase write error -> {_last_error}", file=sys.stderr)


# --------------------------------------------------------------------------- #
# Row builders
# --------------------------------------------------------------------------- #
def _customer_rows(payments: List[Payment]) -> List[Dict]:
    seen: Dict[str, Dict] = {}
    for p in payments:
        seen[p.customer_id] = {
            "customer_id": p.customer_id,
            "previous_successes": p.previous_successes,
            "previous_failures": p.previous_failures,
            "preferred_method": p.preferred_method,
            "base_risk": p.risk_score,
        }
    return list(seen.values())


def _payment_row(p: Payment) -> Dict:
    return {
        "payment_id": p.payment_id,
        "customer_id": p.customer_id,
        "amount": p.amount,
        "currency": p.currency,
        "ts": p.timestamp,
        "payment_method": p.payment_method,
        "status": p.status.value,
        "failure_code": p.failure_code,
        "device": p.device,
        "retry_count": p.retry_count,
        "reminder_count": p.reminder_count,
        "first_failure_ts": p.first_failure_ts,
        "hours_since_first_failure": p.hours_since_first_failure,
        "subscription_id": p.subscription_id,
        "days_overdue": p.days_overdue,
        "risk_score": p.risk_score,
    }


# --------------------------------------------------------------------------- #
# Public API — called by the engine
# --------------------------------------------------------------------------- #
def save_payments(payments: List[Payment]) -> None:
    """Upsert the initial payment universe (customers first for the FK)."""
    if not is_enabled():
        return
    _write("customers", _customer_rows(payments), on_conflict="customer_id")
    _write("payments", [_payment_row(p) for p in payments], on_conflict="payment_id")


def save_recovery(records: List[RecoveryRecord]) -> None:
    """Persist the reasoning + outcome for records the agent just worked."""
    if not is_enabled() or not records:
        return

    diagnoses, decisions, policies, outcomes, audit = [], [], [], [], []
    payments = [r.payment for r in records]

    for r in records:
        if r.diagnosis:
            d = r.diagnosis
            diagnoses.append({
                "payment_id": d.payment_id,
                "category": d.category.value,
                "human_reason": d.human_reason,
                "confidence": d.confidence,
                "evidence": [e.model_dump() for e in d.evidence],
                "source": d.source,
            })
        if r.decision:
            dec = r.decision
            decisions.append({
                "payment_id": dec.payment_id,
                "action": dec.action.value,
                "recovery_probability": dec.recovery_probability,
                "expected_recovery_value": dec.expected_recovery_value,
                "recovery_priority": dec.recovery_priority,
                "rationale": list(dec.rationale),
                "source": dec.source,
            })
        if r.policy:
            pol = r.policy
            policies.append({
                "payment_id": r.payment.payment_id,
                "allowed": pol.allowed,
                "requires_human_approval": pol.requires_human_approval,
                "terminal_action": pol.terminal_action.value if pol.terminal_action else None,
                "checks": [c.model_dump() for c in pol.checks],
            })
        if r.outcome:
            o = r.outcome
            outcomes.append({
                "payment_id": o.payment_id,
                "action": o.action.value,
                "executed": o.executed,
                "success": o.success,
                "recovered_amount": o.recovered_amount,
                "message": o.message,
                "failure_reason": o.failure_reason,
            })
            for a in o.audit:
                audit.append({
                    "ts": a.ts, "payment_id": a.payment_id,
                    "stage": a.stage, "message": a.message,
                })

    # Payment status may have flipped to RECOVERED — upsert it again.
    _write("payments", [_payment_row(p) for p in payments], on_conflict="payment_id")
    _write("diagnoses", diagnoses)
    _write("decisions", decisions)
    _write("policy_evaluations", policies)
    _write("outcomes", outcomes)
    _write("audit_log", audit)
