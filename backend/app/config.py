"""Central configuration for RecoverAI."""
from __future__ import annotations
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def _b(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
RAZORPAY_MODE = os.getenv("RAZORPAY_MODE", "test").strip().lower()
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()
RAZORPAY_FETCH_COUNT = int(os.getenv("RAZORPAY_FETCH_COUNT", "100") or "100")
RAZORPAY_FETCH_DAYS = int(os.getenv("RAZORPAY_FETCH_DAYS", "90") or "90")
RECOVERAI_NOTIFY = _b("RECOVERAI_NOTIFY", "0")
RECOVERAI_SIMULATE_COMPLETION = _b("RECOVERAI_SIMULATE_COMPLETION", "1")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip() or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
NVIDIA_API_URL = os.getenv("NVIDIA_API_URL", "https://integrate.api.nvidia.com/v1/chat/completions").strip().rstrip("/")
RECOVERAI_LLM_MODEL = os.getenv("RECOVERAI_LLM_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b").strip()


def razorpay_enabled() -> bool:
    return bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)


def razorpay_mode_effective() -> str:
    if RAZORPAY_KEY_ID.startswith("rzp_live_"):
        return "live"
    if RAZORPAY_KEY_ID.startswith("rzp_test_"):
        return "test"
    return RAZORPAY_MODE or "test"


def supabase_enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)


def llm_enabled() -> bool:
    return _b("RECOVERAI_USE_LLM", "0") and bool(NVIDIA_API_KEY)


def status() -> dict:
    return {
        "data_source": "razorpay" if razorpay_enabled() else "synthetic",
        "razorpay_mode": razorpay_mode_effective() if razorpay_enabled() else None,
        "webhook": "configured" if RAZORPAY_WEBHOOK_SECRET else "not_configured",
        "persistence": "supabase" if supabase_enabled() else "memory",
        "reasoning": "llm:nemotron-3.5-lightning" if llm_enabled() else "simulated",
        "llm_model": RECOVERAI_LLM_MODEL if llm_enabled() else None,
    }
