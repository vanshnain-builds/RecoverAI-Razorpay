"""Chooses where payments come from: real Razorpay when configured, otherwise
the seeded synthetic dataset. Always returns a (payments, source_label) pair and
never raises — if a real fetch fails or comes back empty, we fall back so the
demo is never blank.
"""
from __future__ import annotations

import sys
from typing import List, Tuple

from . import config, razorpay_client
from .dataset import generate_dataset
from .models import Payment


def load_payments(n_payments: int = 1000, seed: int = 42) -> Tuple[List[Payment], str]:
    if razorpay_client.is_enabled():
        try:
            payments = razorpay_client.fetch_failed_payments()
            failed = [p for p in payments if p.status.value == "failed"]
            if payments and failed:
                print(
                    f"[RecoverAI] Loaded {len(payments)} Razorpay payments "
                    f"({len(failed)} failed) in {config.razorpay_mode_effective()} mode.",
                    file=sys.stderr,
                )
                return payments, "razorpay"
            print(
                "[RecoverAI] Razorpay returned no failed payments in the window; "
                "falling back to synthetic data. Generate some test failures or "
                "increase RAZORPAY_FETCH_DAYS to use real data.",
                file=sys.stderr,
            )
        except Exception as exc:  # noqa: BLE001
            print(
                f"[RecoverAI] Razorpay fetch failed ({exc!r}); using synthetic data.",
                file=sys.stderr,
            )
    return generate_dataset(n_payments, seed), "synthetic"
