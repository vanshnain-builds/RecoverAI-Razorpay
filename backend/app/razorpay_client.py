"""Razorpay integration (test mode by default).

Two real capabilities, both gated on RAZORPAY_KEY_ID/SECRET being present:

  * fetch_failed_payments() — pulls real payments via the Fetch Payments API and
    maps each Razorpay payment object onto our Payment model. Razorpay does not
    hand us the customer history / risk our agent reasons over, so we derive
    those from the fetched window (per-contact success/failure counts, preferred
    method) and translate Razorpay's error fields into our failure vocabulary.

  * create_payment_link() — creates a REAL Razorpay Payment Link (in test mode,
    a real test link) for the send_payment_link action, and returns its short_url.

Everything is wrapped so a missing SDK, bad key, or network error raises and the
caller falls back to the synthetic dataset / mock action. The base project stays
runnable with no key and no network.

Note on honesty: creating a link is a real side effect; whether the customer
then pays can only be confirmed by a webhook. See config.RECOVERAI_SIMULATE_COMPLETION.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import config
from .models import Payment, PaymentStatus

# --------------------------------------------------------------------------- #
# Map Razorpay error signals -> one of OUR failure codes (dataset.FAILURE_CODES),
# so the existing diagnosis agent works unchanged on real data.
# --------------------------------------------------------------------------- #
_REASON_TO_CODE = {
    # customer action
    "insufficient_funds": "insufficient_funds",
    "incorrect_otp": "otp_not_entered",
    "invalid_otp": "otp_not_entered",
    "payment_cancelled": "authentication_abandoned",
    "auto_capture_failed": "authentication_abandoned",
    "3ds_authentication_failed": "authentication_abandoned",
    "payment_authentication_failed": "authentication_abandoned",
    # method / instrument
    "card_declined": "card_declined",
    "declined_by_bank": "card_declined",
    "card_expired": "card_expired",
    "invalid_card": "invalid_card",
    "invalid_card_details": "invalid_card",
    "international_transaction_not_allowed": "invalid_card",
    "payment_method_not_enabled": "invalid_card",
    # temporary / infra
    "gateway_error": "gateway_timeout",
    "gateway_timeout": "gateway_timeout",
    "bank_error": "bank_error_window",
    "server_error": "network_error",
    "network_error": "network_error",
    # subscription / mandate
    "mandate_revoked": "mandate_revoked",
    "mandate_expired": "mandate_expired",
    "recurring_declined": "recurring_declined",
    # risk / fraud
    "risk_blocked": "risk_blocked",
    "suspected_fraud": "suspicious_activity",
    "velocity_exceeded": "velocity_exceeded",
    "payment_fraud": "suspicious_activity",
}

_RISKY_CODES = {"risk_blocked", "suspicious_activity", "velocity_exceeded"}


def is_enabled() -> bool:
    return config.razorpay_enabled()


def _client():
    import razorpay  # imported lazily so base install stays light/offline-safe

    client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))
    try:
        client.set_app_details({"title": "RecoverAI", "version": "1.0.0"})
    except Exception:  # noqa: BLE001
        pass
    return client


def _translate_code(item: Dict) -> str:
    """Best-effort translation of Razorpay error fields to our failure codes."""
    reason = (item.get("error_reason") or "").strip().lower()
    code = (item.get("error_code") or "").strip().lower()
    source = (item.get("error_source") or "").strip().lower()

    if reason in _REASON_TO_CODE:
        return _REASON_TO_CODE[reason]

    # Keyword fallback on reason/description.
    blob = " ".join(
        str(item.get(k, "")) for k in ("error_reason", "error_description", "error_step")
    ).lower()
    if any(w in blob for w in ("fraud", "risk", "velocity", "suspicious")):
        return "risk_blocked"
    if any(w in blob for w in ("otp", "authentication", "3ds", "cancel")):
        return "authentication_abandoned"
    if any(w in blob for w in ("insufficient", "balance", "funds")):
        return "insufficient_funds"
    if any(w in blob for w in ("expired",)):
        return "card_expired"
    if any(w in blob for w in ("declin", "invalid card", "card")):
        return "card_declined"
    if any(w in blob for w in ("mandate", "recurring", "subscription")):
        return "recurring_declined"
    if any(w in blob for w in ("timeout", "gateway", "network", "server")):
        return "gateway_timeout"

    # Fall back on the error source.
    if source in ("bank", "gateway"):
        return "network_error"
    if source == "customer":
        return "authentication_abandoned"
    return "unknown_error" if (reason or code) else "unspecified"


def _contact_key(item: Dict) -> str:
    return (item.get("email") or item.get("contact") or "rzp_customer").strip()


def _build_customer_index(items: List[Dict]) -> Dict[str, Dict]:
    """Derive per-customer signal (history + preferred method) from the window."""
    idx: Dict[str, Dict] = {}
    for it in items:
        key = _contact_key(it)
        c = idx.setdefault(
            key, {"success": 0, "failure": 0, "methods": {}}
        )
        status = (it.get("status") or "").lower()
        if status in ("captured", "authorized", "refunded"):
            c["success"] += 1
            m = (it.get("method") or "").lower()
            if m:
                c["methods"][m] = c["methods"].get(m, 0) + 1
        elif status == "failed":
            c["failure"] += 1
    for c in idx.values():
        c["preferred"] = max(c["methods"], key=c["methods"].get) if c["methods"] else None
    return idx


def _to_payment(item: Dict, cust: Dict, retry_count: int) -> Payment:
    created = int(item.get("created_at") or time.time())
    ts = datetime.fromtimestamp(created, tz=timezone.utc)
    hours_since = max(0.0, (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0)
    status = (item.get("status") or "").lower()
    failed = status == "failed"

    code = _translate_code(item) if failed else None
    risk = 0.0
    if failed:
        risk = 0.82 if code in _RISKY_CODES else 0.12
        # New/low-history customers carry marginally more inherent risk.
        if cust.get("success", 0) == 0:
            risk = min(0.99, risk + 0.08)

    return Payment(
        payment_id=item.get("id") or f"pay_{created}",
        customer_id=_contact_key(item),
        amount=round(float(item.get("amount", 0)) / 100.0, 2),  # paise -> rupees
        currency=item.get("currency") or "INR",
        timestamp=ts.isoformat(timespec="seconds"),
        payment_method=(item.get("method") or "unknown").lower(),
        status=PaymentStatus.FAILED if failed else PaymentStatus.SUCCESS,
        failure_code=code,
        device=None,
        previous_successes=max(0, cust.get("success", 0) - (0 if failed else 1)),
        previous_failures=max(0, cust.get("failure", 0) - (1 if failed else 0)),
        preferred_method=cust.get("preferred"),
        retry_count=retry_count,
        reminder_count=0,
        first_failure_ts=ts.isoformat(timespec="seconds") if failed else None,
        hours_since_first_failure=round(hours_since, 1) if failed else 0.0,
        subscription_id=None,
        days_overdue=0,
        risk_score=round(risk, 3),
    )


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    """Verify a Razorpay webhook using HMAC-SHA256 over the raw request body."""
    secret = config.RAZORPAY_WEBHOOK_SECRET
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


def fetch_failed_payments() -> List[Payment]:
    """Pull a recent window of real payments and map to our Payment model.

    Returns both successes (for customer history/context) and failures (the
    recovery universe). Raises on any error so the caller can fall back.
    """
    client = _client()
    frm = int(time.time()) - config.RAZORPAY_FETCH_DAYS * 86400
    resp = client.payment.all({"count": config.RAZORPAY_FETCH_COUNT, "from": frm})
    items = resp.get("items", []) if isinstance(resp, dict) else []

    cust_index = _build_customer_index(items)
    # Count prior failed attempts per contact so we can approximate retry_count.
    seen_failures: Dict[str, int] = {}
    payments: List[Payment] = []
    # Oldest first so retry_count grows with each subsequent failure.
    for it in sorted(items, key=lambda x: int(x.get("created_at") or 0)):
        key = _contact_key(it)
        retry = seen_failures.get(key, 0) if (it.get("status") == "failed") else 0
        payments.append(_to_payment(it, cust_index.get(key, {}), retry))
        if it.get("status") == "failed":
            seen_failures[key] = seen_failures.get(key, 0) + 1
    return payments


def create_payment_link(payment: Payment) -> Optional[str]:
    """Create a real Razorpay Payment Link and return its short_url.

    Raises on error so the executor can fall back to a simulated link.
    """
    client = _client()
    body: Dict = {
        "amount": int(round(payment.amount * 100)),  # rupees -> paise
        "currency": payment.currency or "INR",
        "accept_partial": False,
        "description": f"RecoverAI recovery for {payment.payment_id}",
        "notify": {"sms": config.RECOVERAI_NOTIFY, "email": config.RECOVERAI_NOTIFY},
        "reminder_enable": False,
        "notes": {"recoverai": "true", "source_payment_id": payment.payment_id},
    }
    customer: Dict = {}
    cid = (payment.customer_id or "").strip()
    if "@" in cid:
        customer["email"] = cid
    elif cid and cid != "rzp_customer":
        customer["contact"] = cid
    if customer:
        body["customer"] = customer

    resp = client.payment_link.create(body)
    if isinstance(resp, dict):
        return resp.get("short_url") or resp.get("id")
    return None
