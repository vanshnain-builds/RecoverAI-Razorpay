"""Central configuration — reads secrets and feature toggles from the
environment (or a local .env file), never from code.

Nothing here is a secret; the *values* come from env vars you set locally, e.g.
in backend/.env (which is gitignored). See backend/.env.example for the full
list. Every integration is OFF unless its keys are present, so the project runs
with zero configuration (synthetic data + in-memory) exactly as before.
"""
from __future__ import annotations

import os

# Load backend/.env if python-dotenv is installed. Optional: if the package or
# the file is absent we silently continue with real environment variables.
try:  # pragma: no cover - trivial
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # noqa: BLE001
    pass


def _b(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


# --------------------------------------------------------------------------- #
# Razorpay (test mode by default). Ingest real payments + create real links.
# --------------------------------------------------------------------------- #
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
RAZORPAY_MODE = os.getenv("RAZORPAY_MODE", "test").strip().lower()
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()

# How much history to pull, and how far back (Razorpay caps a page at 100).
RAZORPAY_FETCH_COUNT = int(os.getenv("RAZORPAY_FETCH_COUNT", "100") or "100")
RAZORPAY_FETCH_DAYS = int(os.getenv("RAZORPAY_FETCH_DAYS", "90") or "90")

# Whether payment links actually notify the customer (SMS/email). Default OFF so
# a demo never messages a real person, even if a real contact slips in.
RECOVERAI_NOTIFY = _b("RECOVERAI_NOTIFY", "0")

# In real mode a payment link's *completion* can only be confirmed by a webhook
# (a customer actually paying). For a self-contained demo we simulate completion
# using the executor's odds. Set to 0 to instead leave real links as PENDING.
RECOVERAI_SIMULATE_COMPLETION = _b("RECOVERAI_SIMULATE_COMPLETION", "1")

# --------------------------------------------------------------------------- #
# Supabase persistence (write-through via PostgREST). Off unless configured.
# --------------------------------------------------------------------------- #
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip()


def razorpay_enabled() -> bool:
    return bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)


def razorpay_mode_effective() -> str:
    """Infer mode from the key prefix (rzp_test_/rzp_live_) and reconcile with
    RAZORPAY_MODE so we can warn on a mismatch."""
    if RAZORPAY_KEY_ID.startswith("rzp_live_"):
        return "live"
    if RAZORPAY_KEY_ID.startswith("rzp_test_"):
        return "test"
    return RAZORPAY_MODE or "test"


def supabase_enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)


def llm_enabled() -> bool:
    return _b("RECOVERAI_USE_LLM", "0") and bool(
        os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
    )


def status() -> dict:
    """Non-secret snapshot of what's wired, for /api/health and the UI badge."""
    return {
        "data_source": "razorpay" if razorpay_enabled() else "synthetic",
        "razorpay_mode": razorpay_mode_effective() if razorpay_enabled() else None,
        "webhook": "configured" if RAZORPAY_WEBHOOK_SECRET else "not_configured",
        "persistence": "supabase" if supabase_enabled() else "memory",
        "reasoning": "llm" if llm_enabled() else "simulated",
    }
