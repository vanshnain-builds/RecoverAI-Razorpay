# RecoverAI — Implementation Blueprint

This is the build spec behind the working prototype in this repo: the exact
pages, data model, API endpoints, agent prompts, policy rules, tech stack, and a
48-hour execution sequence. It intentionally scopes to **one** thing done well —
*payment failure → autonomous recovery* — with an architecture that extends
later to abandoned checkouts, failed subscriptions, and overdue receivables.

---

## 1. Product in one line

Detect revenue slipping away → understand why → choose the best recovery action
→ execute it safely → measure the money recovered.

The differentiator is a **decision-making / optimization layer**, not an LLM
wrapped around payment APIs:

```
Recovery Priority = Expected Recovered Revenue × Success Probability − Risk/Cost
```

The agent doesn't just ask *"can I recover this?"* — it asks *"what should I
recover first, with which action, and when should I stop?"*

---

## 2. Architecture

```
                       ┌───────────────┐
                       │   Merchant UI │  React + Vite (or demo.html)
                       └───────┬───────┘
                               │  HTTP/JSON
                       ┌───────▼───────┐
                       │  FastAPI app  │  app/main.py
                       └───────┬───────┘
              ┌────────────────┴────────────────┐
              ▼                                  ▼
     ┌─────────────────┐                ┌─────────────────┐
     │ Recovery Agent  │  reasoning     │ Policy Engine   │  deterministic
     │ diagnose/decide │                │ retry/window/…  │
     └────────┬────────┘                └────────┬────────┘
              │            ┌───────────────┐     │
              └───────────►│ Action Router │◄────┘
                           │  (executor)   │
                           └───────┬───────┘
                                   ▼
                          ┌────────────────┐
                          │ Mock Razorpay  │  seedable simulator
                          └────────┬───────┘
                                   ▼
                          ┌────────────────┐
                          │ Outcome Tracker│  → Recovery Metrics
                          └────────────────┘
```

**Separation of concerns is the point.** Reasoning is probabilistic and
explainable; safety and money-counting are deterministic and auditable.

---

## 3. Data model

For the prototype, state is in-memory (`RecoveryEngine.records`), but the shapes
map 1:1 onto these tables for a real deployment.

### `payments`
| column | type | notes |
|---|---|---|
| payment_id | PK, text | e.g. `RZP-10482` |
| customer_id | FK → customers | |
| amount | numeric | ₹ |
| currency | text | default INR |
| timestamp | timestamptz | attempt time |
| payment_method | text | upi / card / netbanking / wallet |
| status | enum | success, failed, recovered, escalated, abandoned, pending |
| failure_code | text | e.g. `bank_timeout`, `card_declined` |
| device | text | android / ios / web |
| retry_count | int | attempts already made |
| reminder_count | int | reminders already sent |
| first_failure_ts | timestamptz | anchors the recovery window |
| hours_since_first_failure | numeric | derived |
| subscription_id | FK, nullable | for recurring |
| days_overdue | int | for receivables/subscriptions |
| risk_score | numeric | 0..1 |

### `customers`
| column | type | notes |
|---|---|---|
| customer_id | PK | |
| previous_successes | int | history signal |
| previous_failures | int | history signal |
| preferred_method | text | most-used method |
| base_risk | numeric | 0..1 |

### `diagnoses`
`payment_id`, `category` (enum), `human_reason`, `confidence` (0..1),
`evidence` (json array of `{text, supports_recovery}`), `source` (simulated|llm).

### `decisions`
`payment_id`, `action` (enum), `recovery_probability`, `expected_recovery_value`,
`recovery_priority`, `rationale` (json array), `source`.

### `policy_evaluations`
`payment_id`, `allowed` (bool), `requires_human_approval` (bool),
`terminal_action` (nullable enum), `checks` (json array of `{name, passed, detail}`).

### `outcomes`
`payment_id`, `action`, `executed` (bool), `success` (bool), `recovered_amount`,
`message`, `failure_reason` (nullable).

### `audit_log`
`ts`, `payment_id`, `stage` (detect|diagnose|decide|policy|execute|recover_*),
`message`. Append-only.

### Enums
- **FailureCategory:** `temporary_failure`, `customer_action`,
  `payment_method_issue`, `subscription_failure`, `high_risk`, `unknown`
- **ActionType:** `retry_payment`, `send_payment_link`,
  `suggest_alternate_method`, `send_reminder`, `offer_incentive`,
  `escalate_to_human`, `stop_recovery`

---

## 4. Synthetic dataset (`app/dataset.py`)

- Seeded (`seed=42`) → reproducible demo numbers.
- ~1000 payments, ~15% failed, drawn from a stable customer pool with their own
  history + preferred method + base risk.
- Failure categories distributed to mirror a realistic batch (temporary ~34%,
  customer-action ~25%, method ~20%, subscription ~11%, unknown ~6%, high-risk ~4%).
- Long-tail amounts (mostly small; a few ₹50k–₹1.25L to exercise the high-value
  approval gate).
- The agent is **not** handed the category — it re-derives it, corroborating the
  failure code with independent signals.

---

## 5. Agent design (`app/agent.py`)

### Stage 1 — Diagnose
Start uncertain (0.55), then move confidence with real evidence: customer
history, risk score, method mismatch, transient-error signals. High risk forces
`high_risk`. Output: category + human reason + confidence + evidence list.

### Stage 2 — Predict recovery probability
Base odds per category, nudged by history (+), retries (−), prior failures (−),
and capped low for high-risk.

### Stage 3 — Decide action
Rule-guided selection of the highest expected-value *reasonable* action
(retry / alternate method / payment link / reminder / stop / escalate). The
policy engine still has final say.

### Stage 4 — Explain
Every decision carries a `rationale[]` powering the **Why?** button.

### Expected value + priority
```
expected_recovery_value = amount × recovery_probability
recovery_priority       = expected_value × (1 − effort_penalty) × (1 − risk×0.5)
```

### Hybrid LLM (optional) — prompts in `app/llm_adapter.py`

**Diagnosis system prompt (essence):** classify WHY a payment failed into one of
the six categories; base confidence on corroborating signals, not just the
failure code; high risk ⇒ `high_risk`; do NOT recommend an action. Return strict
JSON `{category, human_reason, confidence, evidence[]}`.

**Decision system prompt (essence):** given a diagnosed payment, choose the
single best recovery action to maximise expected recovered revenue safely;
`high_risk` ⇒ `escalate_to_human`; prefer lowest-friction action with best odds;
you do NOT enforce limits (a separate policy engine does). Return strict JSON
`{action, recovery_probability, rationale[]}`.

On any error or malformed JSON, the code falls back to the simulated engine.

---

## 6. Policy engine (`app/policy.py`) — deterministic, no AI

| Rule | Default | Effect |
|---|---|---|
| MAX_RETRIES | 3 | retry-style actions blocked → STOP |
| MAX_RECOVERY_WINDOW_HOURS | 72 | past window → STOP |
| MAX_REMINDERS | 2 | reminder actions blocked → STOP |
| HIGH_VALUE_THRESHOLD | ₹50,000 | requires human approval |
| SUSPICIOUS_RISK_THRESHOLD | 0.70 | no auto-recovery → ESCALATE |

Returns `allowed`, `requires_human_approval`, `terminal_action`, and an itemised
`checks[]` list (each with name, passed, detail) surfaced in the UI.

---

## 7. Executor + safe failure (`app/executor.py`)

- Only layer that mutates payment state; talks to the seedable mock simulator.
- Recovered amount is deterministic: `recovered_amount = payment.amount` on success.
- **Forced-failure path** (demo "Simulate API failure"): marks executed-but-failed,
  and audits: *did not retry repeatedly · preserved transaction state · scheduled
  next eligible window · logged failure*.
- `final_status`: success→`recovered`; escalate→`escalated`; stop→`abandoned`;
  executed-not-completed→`pending`.

---

## 8. Metrics (`app/engine.py`)

```
revenue_at_risk     = Σ amount of originally-failed payments
recoverable_total   = Σ amount where recovery_probability ≥ 0.35
recoverable_amount  = recoverable_total − recovered_amount   (still open)
recovered_amount    = Σ recovered_amount of successful recoveries
recovery_rate       = recovered_amount / recoverable_total
```
Plus escalated_amount, abandoned_amount, counts, and the funnel
(failed→diagnosed→recoverable→actions_executed→recovered).

---

## 9. Pages / UI

1. **Command Center** — money metrics, the recovery pipeline funnel, category
   breakdown, and *Recover eligible payments* (batch).
2. **Recovery Queue** — payments ranked by `recovery_priority` (expected value
   first), with recommended action per row.
3. **Investigation** — one payment: details, AI diagnosis + evidence, decision
   with **Why?**, deterministic policy checks, and Execute (normal or
   *Simulate API failure*), showing the per-payment audit trail.
4. **Audit Trail** — every action across the session, timestamped.
5. **Ask RecoverAI** — natural-language front door to the same engine.

---

## 10. API

See README for the full table. The contract mirrors the loop:
metrics/pipeline/categories/queue (read), payments + payment detail (diagnose on
demand), recover one / recover batch (execute), audit (observe), chat, reset.

---

## 11. Tech stack

- **Backend:** Python 3.10+, FastAPI, Pydantic v2, Uvicorn. No DB for the
  prototype (in-memory, seeded); Postgres maps cleanly via the tables above.
- **Frontend:** React 18 + Vite. Dev proxy `/api → :8000`. Plus a dependency-free
  `demo.html` fallback so the UI runs with zero install.
- **AI:** simulated reasoning by default; optional Anthropic/OpenAI via env vars.

---

## 12. 48-hour execution sequence

**Day 1 — Intelligence**
- *Morning:* dataset generator — realistic successes/failures, customer history,
  failure reasons, retries, amounts, timestamps.
- *Afternoon:* Recovery Agent — diagnose → probability → choose action → explain.
- *Evening:* Policy Engine (limits, window, approvals, risk) + action simulator/API.

**Day 2 — Product**
- *Morning:* dashboard (revenue at risk / recoverable / recovered / rate) + queue.
- *Afternoon:* investigation view (AI reasoning + audit) + action execution.
- *Evening:* polish the exact demo flow (7 scenes). Don't add features in the
  final hours — make the existing flow airtight.

---

## 13. Mapping to judging criteria

| Criterion | How RecoverAI answers it |
|---|---|
| Problem taste | Real merchant pain: revenue leakage from failed/abandoned payments |
| Build quality | End-to-end agent + backend + dashboard + execution, verified |
| AI judgment | AI diagnoses & chooses; deterministic rules handle safety & money |
| Failure recovery | Forced API failure, retry limits, escalation, stopping rules |
| Measured impact | ₹ at risk → ₹ recoverable → ₹ actually recovered |
| Compliance | Bounded actions, approval thresholds, append-only audit trail |
| Agentic behavior | Detect → diagnose → decide → execute → observe, with prioritisation |
| Razorpay relevance | Payment/recovery workflow modelled on the payment ecosystem |

---

## 14. Extensibility (stated, not built)

The same engine generalises: swap the dataset source and add category handlers
for **abandoned checkout**, **failed subscriptions**, and **overdue B2B
receivables**. The agent → policy → executor → outcome loop stays identical;
only the failure taxonomy and available actions grow.
