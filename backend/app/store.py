"""Supabase persistence — write-through via PostgREST.

RecoverAI keeps its fast in-memory engine state and mirrors that state to
Supabase. Persistence is optional: when the Supabase environment variables are
missing, the application continues in demo/in-memory mode.

The backend uses the Supabase service-role key only. It is never exposed to the
frontend. RLS remains enabled in Supabase; service_role is the trusted backend
role used to persist recovery data.
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
    if not rows or not is_enabled():
        return
    try:
        import requests

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
            _last_error = f"{table}: HTTP {resp.status_code} {resp.text[:300]}"
            print(f"[RecoverAI] Supabase write failed -> {_last_error}", file=sys.stderr)
        else:
            _last_error = None
    except Exception as exc:  # noqa: BLE001
        _last_error = f"{table}: {exc!r}"
        print(f"[RecoverAI] Supabase write error -> {_last_error}", file=sys.stderr)


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


def save_payments(payments: List[Payment]) -> None:
    """Upsert customers and the payment universe."""
    if not is_enabled():
        return
    _write("customers", _customer_rows(payments), on_conflict="customer_id")
    _write("payments", [_payment_row(p) for p in payments], on_conflict="payment_id")


def save_recovery(records: List[RecoveryRecord]) -> None:
    """Persist the reasoning, policy, outcome and audit events for records worked."""
    if not is_enabled() or not records:
        return

    diagnoses: List[Dict] = []
    decisions: List[Dict] = []
    policies: List[Dict] = []
    outcomes: List[Dict] = []
    audit: List[Dict] = []

    for r in records:
        p = r.payment
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
                "payment_id": p.payment_id,
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
                    "ts": a.ts,
                    "payment_id": a.payment_id,
                    "stage": a.stage,
                    "message": a.message,
                })

    # Update payment state after execution and persist all derived records.
    _write("customers", _customer_rows([r.payment for r in records]), on_conflict="customer_id")
    _write("payments", [_payment_row(r.payment) for r in records], on_conflict="payment_id")
    _write("diagnoses", diagnoses)
    _write("decisions", decisions)
    _write("policy_evaluations", policies)
    _write("outcomes", outcomes)
    _write("audit_log", audit)
