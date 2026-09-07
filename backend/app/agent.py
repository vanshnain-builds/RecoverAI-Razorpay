"""RecoverAI reasoning agent: AI diagnosis/decision with deterministic fallback."""
from __future__ import annotations
import os
from typing import List
from .dataset import CODE_TO_CATEGORY
from .models import ActionType, Decision, Diagnosis, Evidence, FailureCategory, Payment

BASE_RECOVERY_ODDS={FailureCategory.TEMPORARY:.82,FailureCategory.CUSTOMER_ACTION:.55,FailureCategory.METHOD_ISSUE:.60,FailureCategory.SUBSCRIPTION:.50,FailureCategory.UNKNOWN:.30,FailureCategory.HIGH_RISK:.10}

def _diagnose_simulated(p:Payment)->Diagnosis:
    c=CODE_TO_CATEGORY.get(p.failure_code or "",FailureCategory.UNKNOWN); e:List[Evidence]=[]; conf=.55
    if p.previous_successes>=3: e.append(Evidence(text=f"Customer has {p.previous_successes} previous successful payments",supports_recovery=True)); conf+=.12
    if p.previous_successes==0: e.append(Evidence(text="First-time customer — limited payment history",supports_recovery=False)); conf-=.05
    if p.risk_score>=.7: c=FailureCategory.HIGH_RISK; e.append(Evidence(text=f"Elevated risk score ({p.risk_score:.2f}) — fraud indicators present",supports_recovery=False)); conf=max(conf,.8)
    elif p.risk_score<.2: e.append(Evidence(text="No unusual account activity detected",supports_recovery=True)); conf+=.05
    if c==FailureCategory.TEMPORARY: e.append(Evidence(text="Failure occurred during a transient bank/network error window",supports_recovery=True)); conf+=.15
    if c==FailureCategory.SUBSCRIPTION and p.subscription_id: e.append(Evidence(text=f"Recurring mandate {p.subscription_id}, {p.days_overdue} days overdue",supports_recovery=True))
    if c==FailureCategory.METHOD_ISSUE and p.preferred_method and p.preferred_method!=p.payment_method: e.append(Evidence(text=f"Customer usually pays via {p.preferred_method.upper()}, not {p.payment_method.upper()}",supports_recovery=True)); conf+=.08
    conf=round(min(.97,max(.4,conf)),2)
    reasons={FailureCategory.TEMPORARY:"Temporary bank/payment network failure",FailureCategory.CUSTOMER_ACTION:"Payment needs a customer action to complete",FailureCategory.METHOD_ISSUE:"Problem with the specific payment instrument used",FailureCategory.SUBSCRIPTION:"Recurring mandate failed to charge",FailureCategory.HIGH_RISK:"Transaction flagged with high-risk / fraud indicators",FailureCategory.UNKNOWN:"Failure cause could not be determined confidently"}
    return Diagnosis(payment_id=p.payment_id,category=c,human_reason=reasons[c],confidence=conf,evidence=e,source="simulated")

def _recovery_probability(p:Payment,d:Diagnosis)->float:
    o=BASE_RECOVERY_ODDS[d.category]+min(.12,p.previous_successes*.015)-min(.20,p.retry_count*.07)-min(.10,p.previous_failures*.03)
    if p.risk_score>=.7:o=min(o,.12)
    return round(min(.97,max(.02,o)),2)

def _choose_action(p:Payment,d:Diagnosis,prob:float):
    if d.category==FailureCategory.HIGH_RISK:return ActionType.ESCALATE_TO_HUMAN,["High-risk indicators present; automatic recovery is unsafe"]
    if p.retry_count>=3:return ActionType.STOP_RECOVERY,["Retry attempts exhausted; further automated retries won't help"]
    if d.category==FailureCategory.TEMPORARY:
        if p.preferred_method and p.preferred_method!=p.payment_method:return ActionType.SUGGEST_ALTERNATE_METHOD,[f"Customer prefers {p.preferred_method.upper()} and it succeeded before","Failure is transient, so an immediate retry has high odds"]
        return ActionType.RETRY_PAYMENT,["Transient failure with strong customer history favours a direct retry"]
    if d.category==FailureCategory.METHOD_ISSUE:return ActionType.SUGGEST_ALTERNATE_METHOD,["Instrument-level failure; steering to an alternate method avoids repeat declines"]
    if d.category==FailureCategory.CUSTOMER_ACTION:
        if p.amount>=10000:return ActionType.SEND_PAYMENT_LINK,["Higher-value, customer-action failure; a payment link is the cleanest path"]
        return ActionType.SEND_REMINDER,["Customer needs to act; a reminder is the lowest-friction nudge"]
    if d.category==FailureCategory.SUBSCRIPTION:return ActionType.RETRY_PAYMENT,["Recurring mandate failure; a staged retry sequence recovers most of these"]
    if prob<.35:return ActionType.STOP_RECOVERY,["Low recovery probability and unclear cause; not worth an automated attempt"]
    return ActionType.SEND_PAYMENT_LINK,["Cause unclear but odds acceptable; a payment link lets the customer self-serve"]

def _decide_simulated(p:Payment,d:Diagnosis)->Decision:
    prob=_recovery_probability(p,d); action,rationale=_choose_action(p,d,prob); expected=round(p.amount*prob,2)
    effort={ActionType.RETRY_PAYMENT:0,ActionType.SUGGEST_ALTERNATE_METHOD:.02,ActionType.SEND_PAYMENT_LINK:.05,ActionType.SEND_REMINDER:.05,ActionType.OFFER_INCENTIVE:.15,ActionType.ESCALATE_TO_HUMAN:0,ActionType.STOP_RECOVERY:0}.get(action,.05)
    return Decision(payment_id=p.payment_id,action=action,recovery_probability=prob,expected_recovery_value=expected,recovery_priority=round(expected*(1-effort)*(1-p.risk_score*.5),2),rationale=rationale,source="simulated")

def _llm_enabled()->bool:
    """Enable the OpenRouter/Nemotron path when explicitly configured.

    The API credential is OPENROUTER_API_KEY. Do not require NVIDIA_API_KEY:
    Nemotron is being accessed through OpenRouter, not NVIDIA's direct endpoint.
    """
    return (
        os.getenv("RECOVERAI_USE_LLM","0").strip().lower() in ("1","true","yes","on")
        and bool(os.getenv("OPENROUTER_API_KEY","").strip())
    )

def diagnose(p:Payment)->Diagnosis:
    if _llm_enabled():
        try:
            from .llm_adapter import llm_diagnose
            return llm_diagnose(p)
        except Exception:
            pass
    return _diagnose_simulated(p)

def decide(p:Payment,d:Diagnosis)->Decision:
    if _llm_enabled():
        try:
            from .llm_adapter import llm_decide
            return llm_decide(p,d)
        except Exception:
            pass
    return _decide_simulated(p,d)
