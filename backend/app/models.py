"""Pydantic models and shared enums for RecoverAI.

These describe the shapes that flow between the dataset, the agent, the policy
engine, the executor and the API. Keeping them in one place makes the contract
between layers explicit.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #
class PaymentStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    # Recovery lifecycle states, layered on top of the raw payment outcome.
    RECOVERED = "recovered"
    ESCALATED = "escalated"
    ABANDONED = "abandoned"
    PENDING = "pending"


class FailureCategory(str, Enum):
    TEMPORARY = "temporary_failure"          # bank/network blip, high recovery odds
    CUSTOMER_ACTION = "customer_action"      # needs the customer to do something
    METHOD_ISSUE = "payment_method_issue"    # card/instrument problem
    SUBSCRIPTION = "subscription_failure"    # recurring mandate failure
    HIGH_RISK = "high_risk"                  # fraud / suspicious indicators
    UNKNOWN = "unknown"


class ActionType(str, Enum):
    RETRY_PAYMENT = "retry_payment"
    SEND_PAYMENT_LINK = "send_payment_link"
    SUGGEST_ALTERNATE_METHOD = "suggest_alternate_method"
    SEND_REMINDER = "send_reminder"
    OFFER_INCENTIVE = "offer_incentive"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    STOP_RECOVERY = "stop_recovery"


# --------------------------------------------------------------------------- #
# Core domain objects
# --------------------------------------------------------------------------- #
class Payment(BaseModel):
    payment_id: str
    customer_id: str
    amount: float
    currency: str = "INR"
    timestamp: str
    payment_method: str
    status: PaymentStatus
    failure_code: Optional[str] = None
    failure_category: Optional[FailureCategory] = None
    device: Optional[str] = None

    # Customer signal, denormalised onto the payment for easy reasoning.
    previous_successes: int = 0
    previous_failures: int = 0
    preferred_method: Optional[str] = None

    # Recovery lifecycle
    retry_count: int = 0
    reminder_count: int = 0
    first_failure_ts: Optional[str] = None
    hours_since_first_failure: float = 0.0

    # Subscription / receivable context
    subscription_id: Optional[str] = None
    days_overdue: int = 0

    # Risk signal
    risk_score: float = 0.0  # 0..1


class Evidence(BaseModel):
    text: str
    supports_recovery: bool = True


class Diagnosis(BaseModel):
    payment_id: str
    category: FailureCategory
    human_reason: str
    confidence: float  # 0..1
    evidence: List[Evidence] = Field(default_factory=list)
    source: str = "simulated"  # "simulated" | "llm"


class Decision(BaseModel):
    payment_id: str
    action: ActionType
    recovery_probability: float          # 0..1
    expected_recovery_value: float       # ₹
    recovery_priority: float             # ranking score
    rationale: List[str] = Field(default_factory=list)
    source: str = "simulated"


class PolicyResult(BaseModel):
    allowed: bool
    checks: List["PolicyCheck"] = Field(default_factory=list)
    requires_human_approval: bool = False
    terminal_action: Optional[ActionType] = None  # forced STOP/ESCALATE if any


class PolicyCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class AuditEntry(BaseModel):
    ts: str
    payment_id: str
    stage: str
    message: str


class ActionOutcome(BaseModel):
    payment_id: str
    action: ActionType
    executed: bool
    success: bool
    recovered_amount: float = 0.0
    message: str = ""
    failure_reason: Optional[str] = None
    audit: List[AuditEntry] = Field(default_factory=list)


class RecoveryRecord(BaseModel):
    """Everything we know about one payment after the agent has run."""
    payment: Payment
    diagnosis: Optional[Diagnosis] = None
    decision: Optional[Decision] = None
    policy: Optional[PolicyResult] = None
    outcome: Optional[ActionOutcome] = None
    final_status: PaymentStatus = PaymentStatus.FAILED


PolicyResult.model_rebuild()
