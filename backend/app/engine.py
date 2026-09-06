"""Recovery engine — orchestration + in-memory store + metrics."""
from __future__ import annotations

import random
import threading
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import agent, config, executor, policy, source, store
from .models import ActionType, AuditEntry, FailureCategory, Payment, PaymentStatus, RecoveryRecord

RECOVERABLE_THRESHOLD = 0.35


class RecoveryEngine:
    def __init__(self, n_payments: int = 1000, seed: int = 42):
        self._lock = threading.Lock()
        self._seed = seed
        self._n_payments = n_payments
        self._rng = random.Random(seed)
        self.records: Dict[str, RecoveryRecord] = {}
        self.global_audit: List[AuditEntry] = []
        self.data_source: str = "synthetic"
        self._initial_payments: List[Payment] = []
        self._load(n_payments, seed)

    def _load(self, n_payments: int, seed: int) -> None:
        payments, src = source.load_payments(n_payments, seed)
        self.data_source = src
        self._initial_payments = deepcopy(payments)
        self.records.clear()
        for p in payments:
            status = PaymentStatus.SUCCESS if p.status == PaymentStatus.SUCCESS else PaymentStatus.FAILED
            self.records[p.payment_id] = RecoveryRecord(payment=deepcopy(p), final_status=status)
        store.save_payments([r.payment for r in self.records.values()])

    def reset(self) -> None:
        with self._lock:
            self._rng = random.Random(self._seed)
            self.global_audit.clear()
            self.records = {}
            for payment in self._initial_payments:
                p = deepcopy(payment)
                status = PaymentStatus.SUCCESS if p.status == PaymentStatus.SUCCESS else PaymentStatus.FAILED
                self.records[p.payment_id] = RecoveryRecord(payment=p, final_status=status)
        store.save_payments([r.payment for r in self.records.values()])

    def status(self) -> Dict:
        """Stable health payload; must never require optional services."""
        return {
            "status": "ready",
            "data_source": self.data_source,
            "razorpay_mode": config.razorpay_mode_effective(),
            "persistence": "supabase" if store.is_enabled() else "memory",
            "reasoning": "llm" if config.llm_enabled() else "simulated",
        }

    def diagnose_and_decide(self, payment_id: str) -> RecoveryRecord:
        rec = self.records[payment_id]
        if rec.payment.status != PaymentStatus.FAILED:
            return rec
        if rec.diagnosis is None:
            rec.diagnosis = agent.diagnose(rec.payment)
        if rec.decision is None:
            rec.decision = agent.decide(rec.payment, rec.diagnosis)
        if rec.policy is None:
            rec.policy = policy.evaluate(rec.payment, rec.decision)
        return rec

    def diagnose_all(self) -> None:
        for pid, rec in self.records.items():
            if rec.payment.status == PaymentStatus.FAILED:
                self.diagnose_and_decide(pid)

    def recover_one(self, payment_id: str, force_failure: bool = False) -> RecoveryRecord:
        with self._lock:
            rec = self.diagnose_and_decide(payment_id)
            if rec.payment.status == PaymentStatus.RECOVERED and rec.outcome and rec.outcome.success:
                return rec
            if rec.decision is None or rec.diagnosis is None or rec.policy is None:
                return rec
            outcome = executor.execute(rec.payment, rec.diagnosis, rec.decision, rec.policy,
                                       force_failure=force_failure, rng=self._rng)
            rec.outcome = outcome
            rec.final_status = executor.final_status(outcome)
            if outcome.success:
                rec.payment.status = PaymentStatus.RECOVERED
            self.global_audit.extend(outcome.audit)
        store.save_recovery([rec])
        return rec

    def confirm_recovery(self, payment_id: str, amount: float, source: str = "razorpay_webhook") -> RecoveryRecord:
        with self._lock:
            rec = self.records.get(payment_id)
            if rec is None:
                raise KeyError(payment_id)
            if rec.payment.status == PaymentStatus.RECOVERED and rec.outcome and rec.outcome.success:
                return rec
            recovered = min(max(float(amount), 0.0), float(rec.payment.amount))
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            if rec.outcome is None:
                rec.outcome = executor.ActionOutcome(
                    payment_id=payment_id, action=ActionType.SEND_PAYMENT_LINK, executed=True,
                    success=True, recovered_amount=recovered,
                    message=f"₹{recovered:,.0f} recovered; verified by Razorpay webhook", audit=[])
            else:
                rec.outcome.success = True
                rec.outcome.recovered_amount = recovered
                rec.outcome.failure_reason = None
                rec.outcome.message = f"₹{recovered:,.0f} recovered; verified by Razorpay webhook"
            rec.payment.status = PaymentStatus.RECOVERED
            rec.final_status = PaymentStatus.RECOVERED
            entry = AuditEntry(ts=now, payment_id=payment_id, stage="recover_success",
                               message=f"Razorpay webhook confirmed payment — ₹{recovered:,.0f} recovered ({source})")
            rec.outcome.audit.append(entry)
            self.global_audit.append(entry)
        store.save_recovery([rec])
        return rec

    def recover_batch(self, limit: Optional[int] = None) -> Dict:
        self.diagnose_all()
        with self._lock:
            eligible = [
                rec for rec in self.records.values()
                if rec.payment.status == PaymentStatus.FAILED
                and (rec.outcome is None or (rec.final_status == PaymentStatus.PENDING
                                             and (rec.outcome.failure_reason or "") != "awaiting_customer_payment"))
            ]
            eligible.sort(key=lambda r: (r.decision.recovery_priority if r.decision else 0), reverse=True)
            if limit:
                eligible = eligible[:limit]
            actions_executed = 0
            for rec in eligible:
                outcome = executor.execute(rec.payment, rec.diagnosis, rec.decision, rec.policy, rng=self._rng)
                rec.outcome = outcome
                rec.final_status = executor.final_status(outcome)
                if outcome.success:
                    rec.payment.status = PaymentStatus.RECOVERED
                if outcome.executed:
                    actions_executed += 1
                self.global_audit.extend(outcome.audit)
        store.save_recovery(eligible)
        m = self.metrics()
        return {
            "analyzed": len(eligible),
            "actions_executed": actions_executed,
            "successful_recoveries": m["recovered_count"],
            "recovered_amount": m["recovered_amount"],
            "still_recoverable": m["remaining_recoverable_amount"],
            "escalated_amount": m["escalated_amount"],
            "abandoned_amount": m["abandoned_amount"],
        }

    def metrics(self) -> Dict:
        revenue_at_risk = 0.0
        recoverable_total = 0.0
        recovered_amount = 0.0
        escalated_amount = 0.0
        abandoned_amount = 0.0
        recovered_count = 0
        failed_count = 0
        actions_executed = 0
        recoverable_count = 0
        remaining_recoverable_count = 0
        original_failed_ids = {p.payment_id for p in self._initial_payments if p.status == PaymentStatus.FAILED}
        original_amounts = {p.payment_id: float(p.amount) for p in self._initial_payments}
        revenue_at_risk = sum(original_amounts.values())
        for payment_id in original_failed_ids:
            r = self.records.get(payment_id)
            if not r:
                continue
            p = r.payment
            if p.status == PaymentStatus.FAILED:
                failed_count += 1
            if r.decision and r.decision.recovery_probability >= RECOVERABLE_THRESHOLD:
                recoverable_total += original_amounts[payment_id]
                recoverable_count += 1
                if r.final_status not in (PaymentStatus.RECOVERED, PaymentStatus.ESCALATED, PaymentStatus.ABANDONED):
                    remaining_recoverable_count += 1
            if r.outcome and r.outcome.executed:
                actions_executed += 1
            if r.final_status == PaymentStatus.RECOVERED:
                recovered_amount += max(0.0, float(r.outcome.recovered_amount if r.outcome else p.amount))
                recovered_count += 1
            elif r.final_status == PaymentStatus.ESCALATED:
                escalated_amount += p.amount
            elif r.final_status == PaymentStatus.ABANDONED:
                abandoned_amount += p.amount
        remaining_recoverable_amount = max(0.0, recoverable_total - recovered_amount)
        recovery_rate = recovered_amount / recoverable_total if recoverable_total else 0.0
        return {
            "at_risk_amount": round(revenue_at_risk, 2),
            "recoverable_total": round(recoverable_total, 2),
            "recovered_amount": round(recovered_amount, 2),
            "remaining_recoverable_amount": round(remaining_recoverable_amount, 2),
            "revenue_at_risk": round(revenue_at_risk, 2),
            "recoverable_amount": round(remaining_recoverable_amount, 2),
            "recovered_count": recovered_count,
            "failed_count": failed_count,
            "actions_executed": actions_executed,
            "recoverable_count": recoverable_count,
            "remaining_recoverable_count": remaining_recoverable_count,
            "escalated_amount": round(escalated_amount, 2),
            "abandoned_amount": round(abandoned_amount, 2),
            "recovery_rate": round(recovery_rate, 4),
        }

    def queue(self, limit: int = 25) -> List[Dict]:
        self.diagnose_all()
        pending = [r for r in self.records.values() if r.payment.status == PaymentStatus.FAILED and r.outcome is None and r.decision]
        pending.sort(key=lambda r: r.decision.recovery_priority, reverse=True)
        return [{
            "payment_id": r.payment.payment_id,
            "amount": r.payment.amount,
            "expected_recovery_value": r.decision.expected_recovery_value,
            "recovery_probability": r.decision.recovery_probability,
            "recovery_priority": r.decision.recovery_priority,
            "action": r.decision.action.value,
            "category": r.diagnosis.category.value if r.diagnosis else None,
        } for r in pending[:limit]]

    def list_payments(self, status: Optional[str] = None, limit: int = 100) -> List[Dict]:
        rows = []
        for r in self.records.values():
            p = r.payment
            if status == "failed" and p.status not in (PaymentStatus.FAILED, PaymentStatus.RECOVERED):
                continue
            if status == "success" and p.status != PaymentStatus.SUCCESS:
                continue
            rows.append({
                "payment_id": p.payment_id,
                "customer_id": p.customer_id,
                "amount": p.amount,
                "payment_method": p.payment_method,
                "status": p.status.value,
                "final_status": r.final_status.value,
                "failure_code": p.failure_code,
                "action": r.decision.action.value if r.decision else None,
                "recovery_probability": r.decision.recovery_probability if r.decision else None,
            })
            if len(rows) >= limit:
                break
        return rows

    def pipeline(self) -> Dict:
        """Return counts for each stage of the recovery pipeline."""
        self.diagnose_all()
        counts = Counter()
        for r in self.records.values():
            if r.payment.status == PaymentStatus.FAILED or r.payment.status == PaymentStatus.RECOVERED:
                counts["detected"] += 1
            if r.diagnosis is not None:
                counts["diagnosed"] += 1
            if r.decision is not None:
                counts["decided"] += 1
            if r.policy is not None:
                counts["policy_checked"] += 1
            if r.outcome is not None and r.outcome.executed:
                counts["executed"] += 1
            if r.final_status == PaymentStatus.RECOVERED:
                counts["recovered"] += 1
            elif r.final_status == PaymentStatus.PENDING:
                counts["pending"] += 1
            elif r.final_status == PaymentStatus.ESCALATED:
                counts["escalated"] += 1
            elif r.final_status == PaymentStatus.ABANDONED:
                counts["abandoned"] += 1
            elif r.payment.status == PaymentStatus.FAILED:
                counts["failed"] += 1
        return dict(counts)

    def category_breakdown(self) -> Dict:
        """Return failed/recoverable payment counts and amounts by AI category."""
        self.diagnose_all()
        out: Dict[str, Dict[str, float | int]] = {}
        for r in self.records.values():
            if r.payment.status not in (PaymentStatus.FAILED, PaymentStatus.RECOVERED):
                continue
            if r.diagnosis is None:
                continue
            key = r.diagnosis.category.value
            row = out.setdefault(key, {"count": 0, "amount": 0.0, "recoverable_count": 0, "recoverable_amount": 0.0})
            row["count"] += 1
            row["amount"] += float(r.payment.amount)
            if r.decision and r.decision.recovery_probability >= RECOVERABLE_THRESHOLD:
                row["recoverable_count"] += 1
                row["recoverable_amount"] += float(r.payment.amount)
        for row in out.values():
            row["amount"] = round(float(row["amount"]), 2)
            row["recoverable_amount"] = round(float(row["recoverable_amount"]), 2)
        return out

    def detail(self, payment_id: str) -> RecoveryRecord:
        return self.diagnose_and_decide(payment_id)


_engine: Optional[RecoveryEngine] = None


def get_engine() -> RecoveryEngine:
    global _engine
    if _engine is None:
        _engine = RecoveryEngine()
    return _engine
