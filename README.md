# RecoverAI — Autonomous Revenue Recovery

> **AI-powered revenue recovery agent that detects failed payments, understands why revenue is at risk, decides the safest recovery action, executes it, and measures the money recovered.**

RecoverAI is built for the **Razorpay AI Revenue Recovery** track. The core idea is simple: **a failed payment should not automatically mean lost revenue**.

Instead of giving a merchant another dashboard that only reports failed payments, RecoverAI creates an intelligent recovery workflow:

**Detect → Diagnose → Decide → Validate → Execute → Verify → Measure**

---

## 🚀 Hackathon Pitch

RecoverAI is an autonomous revenue-recovery system for merchants.

When a payment fails, RecoverAI doesn't just mark it as failed. It analyzes the payment context, including the failure reason, customer history, payment method, retry history and risk information. It then estimates the probability of successful recovery, selects an appropriate intervention, validates that the action follows recovery policies, executes the recovery workflow, and records the complete result in an audit trail.

The goal is to turn **revenue leakage into measurable recovered revenue**.

This directly matches the challenge requirement of detecting revenue at risk, determining the right intervention, executing a bounded recovery workflow, and showing measured money recovered across a batch.

Razorpay's webhook system can provide asynchronous payment-state notifications such as `payment.failed`, while Razorpay's APIs can be used to retrieve payment information and perform supported payment operations. ([Razorpay][1])

---

# 🎯 Problem

Payment failures are not always permanent.

A customer can have a failed payment because of:

* Temporary bank/network problems
* Payment-method issues
* Insufficient funds
* Customer action
* Subscription failures
* Other transient problems

For a merchant, however, these failures can simply appear as:

> **₹75,55,688 failed revenue**

The problem is that traditional systems often stop at detection.

They tell the merchant:

> "This payment failed."

But they don't necessarily answer:

> **Why did it fail?**
> **Can it be recovered?**
> **What should we do next?**
> **Which recovery action should happen first?**
> **Did the recovery actually work?**
> **How much money did we recover?**

RecoverAI closes this loop.

---

# 💡 Solution

RecoverAI introduces an **AI-assisted autonomous recovery agent** between payment failure and revenue recovery.

### The workflow

```text
                    PAYMENT FAILURE
                           │
                           ▼
                    ┌─────────────┐
                    │   DETECT    │
                    │ Revenue at  │
                    │    risk     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  DIAGNOSE   │
                    │ Understand  │
                    │ failure     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   DECIDE    │
                    │ Select best │
                    │ intervention│
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   POLICY    │
                    │ Safety &    │
                    │ boundaries  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   EXECUTE   │
                    │ Recovery    │
                    │ action      │
                    └──────┬──────┘
                           │
                     ┌─────┴─────┐
                     ▼           ▼
                 SUCCESS      PENDING/
                     │         FAILURE
                     ▼           │
               VERIFIED          ▼
                 RECOVERY    NEXT ACTION
                     │
                     └─────┬─────┘
                           ▼
                    ┌─────────────┐
                    │   MEASURE   │
                    │ ₹ recovered │
                    │ + audit log │
                    └─────────────┘
```

This makes RecoverAI more than a payment dashboard.

It is a **bounded revenue-recovery agent**.

---

# 🧠 Why an Agent Instead of a Dashboard?

A normal dashboard:

```text
Payment failed
       ↓
Show merchant
       ↓
Merchant decides what to do
```

RecoverAI:

```text
Payment failed
       ↓
Agent investigates
       ↓
Agent diagnoses
       ↓
Agent calculates recovery opportunity
       ↓
Agent chooses intervention
       ↓
Policy validates action
       ↓
Agent executes
       ↓
Agent verifies result
       ↓
Metrics update
```

The agent is therefore responsible for the **decision loop**, while deterministic policies provide boundaries around what it is allowed to do.

---

# 🏗️ System Architecture

```text
                         ┌─────────────────────┐
                         │      Razorpay       │
                         │                     │
                         │ Payments / Webhooks │
                         └──────────┬──────────┘
                                    │
                              Payment events
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────┐
│                    RecoverAI Backend                    │
│                                                         │
│  ┌─────────────┐       ┌─────────────────────────────┐ │
│  │   Source    │──────▶│      Recovery Engine        │ │
│  └─────────────┘       │                             │ │
│                        │ Detect → Diagnose → Decide  │ │
│                        └──────────────┬──────────────┘ │
│                                       │                 │
│                                       ▼                 │
│                        ┌─────────────────────────────┐ │
│                        │       Policy Engine        │ │
│                        │                             │ │
│                        │ Risk limits                 │ │
│                        │ Retry limits                │ │
│                        │ Action validation           │ │
│                        └──────────────┬──────────────┘ │
│                                       │                 │
│                                       ▼                 │
│                        ┌─────────────────────────────┐ │
│                        │     Recovery Executor       │ │
│                        └──────────────┬──────────────┘ │
│                                       │                 │
│                           ┌───────────┼───────────┐     │
│                           ▼           ▼           ▼     │
│                        Success     Pending     Failure  │
│                           │           │           │     │
│                           └───────────┼───────────┘     │
│                                       ▼                 │
│                              Audit + Metrics            │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
              ┌─────────────────────┐
              │      Supabase       │
              │      PostgreSQL     │
              │                     │
              │ Payments            │
              │ Recovery actions    │
              │ Audit events        │
              └─────────────────────┘
                        │
                        ▼
              ┌─────────────────────┐
              │   React Frontend    │
              │                     │
              │ Command Center      │
              │ Recovery Queue      │
              │ Investigation       │
              │ Audit Trail         │
              │ Ask RecoverAI       │
              └─────────────────────┘
```

---

# 🔄 Core Recovery Loop

## 1. Detect

RecoverAI identifies failed payments and revenue at risk.

Example:

```text
Payment: RZP-10014
Amount: ₹2,999
Status: Failed
Failure: network_error
```

The system doesn't treat every failure identically.

---

## 2. Diagnose

The system analyzes the available payment context.

For example:

```text
Failure:
network_error

Customer history:
10 successful payments
1 previous failure

Risk:
Low

Diagnosis:
temporary_failure

Confidence:
87%
```

This gives the recovery engine context rather than blindly retrying every payment.

---

# 3. Decide

The agent evaluates potential recovery actions.

Example:

```text
Recovery probability: 91%

Recommended action:
retry_payment

Expected recovery:
₹2,729

Priority:
₹2,523
```

The queue can therefore prioritize opportunities according to expected recovered value rather than simply sorting by transaction amount.

---

# 4. Policy Validation

This is an important part of the system.

AI should not have unlimited authority to execute arbitrary financial actions.

RecoverAI therefore introduces a policy layer.

```text
AI decision
     ↓
Policy validation
     ↓
Allowed?
   /   \
 YES    NO
  │      │
  ▼      ▼
Execute  Escalate
```

Example boundaries can include:

* Maximum retry count
* Maximum recovery attempts
* Risk threshold
* Supported recovery action
* Stopping conditions
* Escalation requirements

This gives the system a **bounded autonomy** model.

---

# 5. Execute

Once the action passes policy validation, RecoverAI executes the recovery workflow.

Possible actions include:

```text
retry_payment
request_new_payment_method
send_recovery_link
escalate_to_support
stop_retry
```

The exact action depends on the diagnosis and recovery policy.

---

# 6. Verify

A recovery action is not considered successful merely because the action was initiated.

RecoverAI separates:

### Success

```text
Payment successfully recovered
₹2,999 recovered
```

### Pending

```text
Recovery initiated
Waiting for payment confirmation
```

### Failure

```text
Recovery attempt failed
No revenue recovered
```

This distinction is important because **initiated recovery ≠ recovered revenue**.

---

# 📊 Metrics

RecoverAI deliberately separates the major revenue metrics.

## At Risk

**Original failed-payment amount.**

Example:

```text
₹75,55,688
At risk · original failed revenue
```

This represents the total failed revenue opportunity entering the system.

---

## Recoverable

**AI-identified opportunity above the recovery threshold.**

```text
₹X
Recoverable · identified opportunity
```

This is not the same as total failed revenue.

It represents the portion that the recovery engine considers worth attempting to recover.

---

## Recovered

**Verified successful recovery outcomes.**

```text
₹X
Recovered · verified outcome
```

This is the most important outcome metric.

It should increase only when the recovery result is actually confirmed.

---

## Remaining

**Recoverable revenue that has not yet been recovered.**

```text
₹X
Remaining recoverable
```

The relationship is:

```text
Recoverable
     │
     ├── Recovered
     │
     └── Remaining
```

This makes the dashboard much easier for a merchant or judge to understand.

---

# 📈 Recovery Rate

RecoverAI also displays recovery rate.

Conceptually:

```text
Recovery Rate =
Verified Recovered Revenue
────────────────────────────
Recoverable Revenue
```

This gives the merchant an outcome-based measurement rather than simply counting recovery attempts.

---

# 🖥️ Product Interface

## Command Center

The Command Center is the primary merchant dashboard.

It provides:

* At-risk revenue
* Recoverable revenue
* Recovered revenue
* Remaining recoverable revenue
* Failed payments
* Recovery rate
* Recovery actions
* Recovery pipeline
* Failure categories

The purpose is to answer one question quickly:

> **How much revenue is at risk, and how much of it are we actually recovering?**

### Screenshot

![RecoverAI Command Center](docs/screenshots/command-center.png)

---

# 🔎 Investigation

The Investigation page gives the merchant a deeper explanation of an individual failed payment.

Example:

```text
PAYMENT RZP-10014

Amount
₹2,999

Method
card

Failure code
network_error

Customer history
10 successful / 1 failed

Risk score
0.15
```

Then RecoverAI provides:

```text
AI Diagnosis
temporary failure

Confidence
87%

Reason:
Temporary bank/payment network failure
```

The recovery decision is shown alongside it.

```text
Recovery probability
91%

Recommended action
retry_payment

Expected recovery
₹2,729
```

The interface also exposes the execution sequence:

```text
detect
   ↓
diagnose
   ↓
decide
   ↓
policy
   ↓
execute
   ↓
recover_success
```

### Screenshot

![RecoverAI Investigation](docs/screenshots/investigation.png)

---

# 📋 Recovery Queue

The Recovery Queue is where the agent decides **what to recover first**.

Rather than displaying failed payments randomly, the queue can rank opportunities according to expected recovery value while accounting for risk and operational effort.

Example:

| Payment   | Amount | Category          | Action        | Recovery Probability | Expected ₹ |
| --------- | -----: | ----------------- | ------------- | -------------------: | ---------: |
| RZP-10014 | ₹2,999 | Temporary failure | Retry         |                  91% |     ₹2,729 |
| RZP-10021 | ₹5,499 | Payment issue     | New method    |                  76% |     ₹4,179 |
| RZP-10031 | ₹1,999 | Customer action   | Recovery link |                  68% |     ₹1,359 |

The important concept is:

> **RecoverAI decides what to recover first, not just whether a payment is recoverable.**

### Screenshot

![RecoverAI Recovery Queue](docs/screenshots/recovery-queue.png)

---

# 🧾 Audit Trail

Every recovery decision should be explainable.

RecoverAI records events such as:

```text
DETECT
Payment failure detected

DIAGNOSE
Diagnosed as temporary_failure

DECIDE
Selected retry_payment

POLICY
Policy validation PASSED

EXECUTE
Recovery initiated

RECOVER_SUCCESS
Payment successfully recovered
```

This provides an audit trail for:

* Debugging
* Merchant trust
* Operational review
* AI explainability
* Recovery analysis

---

# 🤖 Ask RecoverAI

The interface also provides an AI assistant for interacting with the recovery system.

Example questions:

```text
Which payment should I recover first?

Why is this payment considered recoverable?

How much revenue is currently at risk?

Why did the agent choose retry_payment?

Which failure category has the highest recovery opportunity?

How much revenue has been recovered?
```

This turns the dashboard from a static reporting tool into an interactive operational interface.

---

# 💳 Razorpay Integration

RecoverAI is designed to work with Razorpay payment data.

Razorpay provides APIs for retrieving payment information and supported payment operations. ([Razorpay][2])

Razorpay also provides webhooks that asynchronously notify applications about payment events.

For example:

```text
Razorpay
   │
   │ payment.failed
   ▼
RecoverAI Webhook
   │
   ▼
Store payment event
   │
   ▼
Diagnose
   │
   ▼
Recovery decision
```

Razorpay specifically documents `payment.failed` as an event that can be used to receive notifications about failed payments. ([Razorpay][1])

### Why Webhooks?

Without webhooks:

```text
RecoverAI → "Did payment fail?"
RecoverAI → "Did payment fail?"
RecoverAI → "Did payment fail?"
```

With webhooks:

```text
Payment changes
      ↓
Razorpay sends event
      ↓
RecoverAI receives event
      ↓
RecoverAI processes it
```

This makes the architecture event-driven.

### Razorpay Webhook Endpoint

Once the backend is deployed, the webhook URL should point to your **public backend endpoint**, not the frontend.

For example:

```text
https://YOUR-BACKEND.onrender.com/api/webhooks/razorpay
```

Use the exact webhook route implemented by your backend.

Razorpay requires webhook endpoints to be publicly accessible and recommends HTTPS. Webhook URLs cannot simply be localhost URLs. ([Razorpay][3])

### Recommended Razorpay events

For this project, the important payment events to consider are:

```text
payment.failed
payment.authorized
payment.captured
order.paid
```

Razorpay documents these payment/order webhook events and their payloads. ([Razorpay][4])

### Test Mode

For the hackathon demonstration, use **Razorpay Test Mode**.

Razorpay provides separate Test and Live API keys, and test-mode webhook events can be used to validate the integration before going live. ([Razorpay][5])

**Important:** Never expose Razorpay secrets in the frontend or commit them to GitHub.

---

# 🗄️ Supabase

RecoverAI uses Supabase as the persistent data layer.

Supabase provides a PostgreSQL database and can be accessed programmatically from the application. ([Supabase][6])

The database stores information such as:

```text
Payments
Recovery decisions
Recovery actions
Audit events
```

Conceptually:

```text
Razorpay Events
       │
       ▼
RecoverAI Backend
       │
       ▼
    Supabase
       │
 ┌─────┼──────┐
 ▼     ▼      ▼
Payments Audit Recovery
       │
       ▼
   Frontend
```

This allows the application to persist recovery state instead of depending entirely on in-memory demo data.

---

# 🧠 AI Layer

The AI layer is responsible for reasoning about the recovery opportunity.

A typical decision flow is:

```text
Payment information
        +
Failure information
        +
Customer history
        +
Retry history
        +
Risk
        ↓
AI Diagnosis
        ↓
Recovery probability
        ↓
Recommended action
```

The AI should be used where judgment is valuable.

Deterministic code should handle things that must be predictable.

### AI is useful for

* Diagnosing failure context
* Selecting an intervention
* Explaining decisions
* Prioritizing recovery opportunities
* Conversational analysis

### Deterministic logic is useful for

* Monetary calculations
* Recovery thresholds
* Retry limits
* State transitions
* Policy enforcement
* Audit logging
* API validation

This hybrid design is intentional.

> **AI provides judgment; deterministic policies provide control.**

---

# 🔐 Safety & Bounded Autonomy

Because RecoverAI operates around financial workflows, unrestricted AI execution would be unsafe.

The architecture therefore follows:

```text
AI recommendation
       ↓
Policy validation
       ↓
Bounded action
       ↓
Execution
       ↓
Verification
```

The agent should not be allowed to:

* Execute unlimited retries
* Ignore risk thresholds
* Perform unsupported actions
* Continue retrying indefinitely
* Treat an initiated action as a successful recovery

Stopping conditions are therefore a fundamental part of the architecture.

---

# 🔄 Recovery State Machine

RecoverAI treats recovery as a state machine.

```text
FAILED
  │
  ▼
DIAGNOSED
  │
  ▼
RECOVERABLE
  │
  ▼
ACTION_SELECTED
  │
  ▼
POLICY_VALIDATED
  │
  ▼
RECOVERY_INITIATED
  │
  ├───────────────┐
  ▼               ▼
SUCCESS         PENDING
  │               │
  ▼               ▼
RECOVERED      WAIT / NEXT ACTION
                  │
                  ▼
                FAILED
```

This prevents ambiguous states.

For example:

**Recovery initiated**

does not automatically become:

**Recovered**

until the payment outcome is verified.

---

# 📊 Failure Categories

RecoverAI groups payment failures into understandable categories.

Examples:

```text
Temporary failure
Customer action
Payment method issue
Subscription failure
Unknown
```

This allows merchants to identify where their revenue leakage is concentrated.

Instead of seeing:

```text
156 random failed payments
```

they can see:

```text
Temporary failures       52
Customer action          38
Payment method issues    25
Subscription failures   22
Unknown                  10
```

This is much more actionable.

---

# 🛠️ Technology Stack

## Frontend

* React
* Vite
* JavaScript
* CSS

## Backend

* Python
* FastAPI
* Uvicorn

## Database

* Supabase
* PostgreSQL

## Payments

* Razorpay APIs
* Razorpay Webhooks

## AI

* LLM-compatible architecture
* AI diagnosis
* AI-assisted recovery decisions
* Conversational assistant

## Deployment

* GitHub
* Render

---

# 📁 Project Structure

```text
RecoverAI-Razorpay/
│
├── README.md
├── BLUEPRINT.md
├── demo.html
├── run.sh
│
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   │
│   └── app/
│       ├── __init__.py
│       ├── agent.py
│       ├── chat.py
│       ├── config.py
│       ├── dataset.py
│       ├── engine.py
│       ├── executor.py
│       ├── llm_adapter.py
│       ├── main.py
│       ├── models.py
│       ├── policy.py
│       ├── razorpay_client.py
│       ├── source.py
│       └── store.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   │
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       ├── main.jsx
│       ├── styles.css
│       │
│       └── components/
│           ├── AuditTrail.jsx
│           ├── Chat.jsx
│           ├── Dashboard.jsx
│           ├── Investigation.jsx
│           └── Queue.jsx
│
└── db/
    └── supabase_schema.sql
```

---

# ⚙️ Local Setup

## 1. Clone

```bash
git clone https://github.com/vanshnain-builds/RecoverAI-Razorpay.git
cd RecoverAI-Razorpay
```

## 2. Backend

```bash
cd backend

python -m venv .venv
```

### Windows

```powershell
.venv\Scripts\activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Environment variables

Create:

```text
backend/.env
```

based on:

```text
backend/.env.example
```

Typical variables include:

```env
SUPABASE_URL=
SUPABASE_KEY=

RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=

RAZORPAY_WEBHOOK_SECRET=

LLM_API_KEY=
```

**Do not commit `.env`.**

Only `.env.example` should be committed.

---

# ▶️ Run Backend

From the backend directory:

```bash
uvicorn app.main:app --reload
```

The API should then be available at:

```text
http://localhost:8000
```

FastAPI also provides interactive API documentation at:

```text
http://localhost:8000/docs
```

Render uses the same FastAPI/Uvicorn model for deployment. ([Render][7])

---

# ▶️ Run Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite will provide the local frontend URL.

During development, the frontend can use the Vite proxy to communicate with:

```text
/api
```

For production, configure:

```env
VITE_API_URL=https://YOUR-BACKEND.onrender.com
```

so requests become:

```text
https://YOUR-BACKEND.onrender.com/api/health
https://YOUR-BACKEND.onrender.com/api/metrics
https://YOUR-BACKEND.onrender.com/api/queue
```

---

# ☁️ Deployment

## Backend — Render

Create a **Render Web Service** connected to your GitHub repository.

Typical configuration:

```text
Root Directory:
backend

Build Command:
pip install -r requirements.txt

Start Command:
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Render's FastAPI documentation uses this Uvicorn production pattern. ([Render][7])

Then add your environment variables in:

```text
Render
→ Service
→ Environment
```

Do not put secrets into GitHub.

---

# 🌐 Frontend — Render

Create another Render service as a **Static Site**.

Typical configuration:

```text
Root Directory:
frontend

Build Command:
npm install && npm run build

Publish Directory:
dist
```

Then add:

```env
VITE_API_URL=https://YOUR-BACKEND.onrender.com
```

The frontend then communicates with the deployed FastAPI backend.

Render supports static sites separately from server-side web services. ([Render][8])

---

# 🔗 Frontend → Backend Connection

The production architecture is:

```text
User
 │
 ▼
React Frontend
 │
 │ HTTPS
 ▼
Render FastAPI Backend
 │
 ├──────────────┐
 ▼              ▼
Supabase      Razorpay
PostgreSQL    APIs/Webhooks
```

The frontend should **never directly contain**:

```text
RAZORPAY_KEY_SECRET
SUPABASE_SERVICE_ROLE_KEY
LLM_SECRET_KEY
```

Those belong on the backend.

---

# 🔔 Webhook Architecture

After deploying the backend, configure Razorpay:

```text
Razorpay Dashboard
        ↓
Account & Settings
        ↓
Webhooks
        ↓
Add New Webhook
```

Set:

```text
Webhook URL:
https://YOUR-BACKEND.onrender.com/<your-webhook-route>
```

Select the relevant payment events.

Razorpay's official setup flow is through **Account & Settings → Webhooks → Add New Webhook**. ([Razorpay][3])

For security, configure a webhook secret and validate the webhook signature on the backend. Razorpay recommends validating webhook requests and testing the integration before relying on it. ([Razorpay][9])

---

# 🧪 Demo Mode

RecoverAI includes synthetic/demo data so the complete recovery workflow can be demonstrated without depending on live customer transactions.

This is particularly useful during a hackathon.

A judge can see:

```text
Failed payments
      ↓
AI diagnosis
      ↓
Recovery queue
      ↓
Recovery action
      ↓
Success / pending / failure
      ↓
Recovered revenue
      ↓
Audit trail
```

The **Reset Demo** functionality restores the initial demonstration state so the complete workflow can be shown repeatedly.

---

# 🧑‍⚖️ Judge Demo Flow

A recommended 2–3 minute live demonstration:

### Step 1 — Command Center

Start on the dashboard.

Explain:

> "This is RecoverAI's Command Center. It gives the merchant a real-time view of revenue at risk, recoverable opportunity, verified recovered revenue and remaining opportunity."

---

### Step 2 — Recovery Queue

Open:

```text
Recovery Queue
```

Explain:

> "Instead of treating all failed payments equally, RecoverAI prioritizes them based on expected recovery value, risk and the selected intervention."

---

### Step 3 — Investigation

Select a payment.

Show:

```text
Failure reason
Customer history
Risk score
AI diagnosis
Recovery probability
Recommended action
Expected recovery
```

Explain:

> "The agent doesn't blindly retry. It first diagnoses the failure and determines whether a recovery action is justified."

---

### Step 4 — Explainability

Show:

```text
detect
diagnose
decide
policy
execute
recover_success
```

Explain:

> "Every important decision is visible and auditable."

---

### Step 5 — Execute

Click the recovery action.

Show:

```text
Recovery initiated
```

Then demonstrate:

```text
Success
```

or:

```text
Pending
```

or:

```text
Failure
```

Explain:

> "The system distinguishes between an action being initiated and revenue actually being recovered."

---

### Step 6 — Metrics

Return to Command Center.

Show:

```text
At Risk
Recoverable
Recovered
Remaining
Recovery Rate
```

Explain:

> "This is the key business outcome. We're not measuring AI activity—we're measuring recovered revenue."

---

### Step 7 — Audit Trail

Open:

```text
Audit Trail
```

Explain:

> "Every recovery attempt and decision is recorded, giving the merchant an auditable history of what the agent did and why."

---

# 🏆 Why RecoverAI Fits the Razorpay Challenge

The challenge asks builders to create an agent that can:

```text
Detect revenue at risk
        ↓
Determine intervention
        ↓
Execute bounded recovery
        ↓
Show measured recovered money
```

RecoverAI maps directly onto that requirement:

| Challenge Requirement  | RecoverAI                   |
| ---------------------- | --------------------------- |
| Detect revenue at risk | Failed payment detection    |
| Diagnose problem       | AI diagnosis                |
| Determine intervention | Recovery decision engine    |
| Execute workflow       | Recovery executor           |
| Bounded execution      | Policy engine               |
| Handle outcomes        | Success / pending / failure |
| Measure revenue        | Recovery metrics            |
| Batch prioritization   | Recovery Queue              |
| Explain decisions      | Investigation               |
| Auditability           | Audit Trail                 |
| Payment integration    | Razorpay API/webhooks       |
| Persistent state       | Supabase                    |

---

# 💰 Business Value

For merchants, even a small recovery improvement can have significant impact.

Imagine:

```text
₹10,00,000 failed revenue
```

If RecoverAI identifies:

```text
₹6,00,000 recoverable opportunity
```

and successfully recovers:

```text
₹3,00,000
```

then the system has transformed previously lost revenue into:

```text
₹3,00,000 recovered revenue
```

The important metric is therefore not:

> "How many AI decisions did we make?"

It is:

> **"How much revenue did we successfully recover?"**

---

# 📈 Future Improvements

The current architecture can be extended into a production-grade system.

## 1. Real-time Razorpay Event Processing

Move from synthetic events to continuous webhook-driven payment events.

```text
payment.failed
      ↓
RecoverAI
      ↓
Automatic diagnosis
      ↓
Recovery decision
```

---

## 2. Better Recovery Prediction

Train a dedicated recovery-probability model using historical merchant data.

Potential features:

```text
Payment amount
Failure code
Payment method
Customer history
Time of day
Retry count
Previous recovery behaviour
Subscription status
Risk signals
```

---

## 3. Adaptive Recovery

Instead of using one static retry strategy:

```text
Attempt 1
   ↓
Outcome
   ↓
Update probability
   ↓
Choose next action
```

The agent can adapt its strategy based on the latest outcome.

---

## 4. Merchant-Specific Policies

Different merchants may require different rules.

For example:

```text
Merchant A
Maximum retries = 2

Merchant B
Maximum retries = 3

Merchant C
High-value payments require manual approval
```

---

## 5. Recovery Experimentation

The system could eventually compare strategies:

```text
Strategy A → Retry
Strategy B → Payment link
Strategy C → Alternative method
```

and measure:

```text
Recovery rate
Revenue recovered
Customer response
Operational cost
```

---

## 6. Real-Time Analytics

Future dashboards could show:

```text
Revenue recovered today
Recovery rate
Best-performing intervention
Top failure category
Revenue at risk
Revenue recovered by category
```

---

# 🔐 Security Considerations

Financial systems require careful handling of secrets and customer data.

RecoverAI follows the principle:

```text
Frontend
   │
   │ Public configuration only
   ▼
Backend
   │
   ├── Razorpay secrets
   ├── Supabase server credentials
   ├── LLM credentials
   └── Business policies
```

Secrets should be stored as environment variables and never committed to GitHub.

Razorpay's documentation explicitly recommends securely storing API credentials and notes that the secret is only displayed when the key is generated. ([Razorpay][5])

---

# ⚠️ Current Scope & Limitations

RecoverAI is a hackathon prototype rather than a production payment-recovery platform.

The architecture demonstrates the complete decision and recovery workflow using the available demo/synthetic data and integration points.

Before production deployment, additional work would be required around:

* Production-grade authentication
* Fine-grained authorization
* Comprehensive webhook signature validation
* Idempotent event processing
* Retry scheduling
* Distributed job processing
* Rate limiting
* Monitoring
* Secret management
* Extensive payment-provider testing
* Compliance requirements
* Human approval workflows for sensitive actions

This distinction is intentional: the hackathon demonstrates the **agentic recovery architecture and measurable recovery workflow** without pretending that a prototype should automatically control real production funds.

---

# 🧩 Design Philosophy

RecoverAI follows five principles:

### 1. Detect before acting

Don't execute blindly.

### 2. Diagnose before retrying

Understand the likely reason for failure.

### 3. AI recommends, policy controls

AI provides judgment while deterministic rules enforce boundaries.

### 4. Initiated ≠ recovered

Only verified outcomes count toward recovered revenue.

### 5. Every action should be explainable

The merchant should be able to understand what happened.

---

# 🎬 One-Line Explanation

> **RecoverAI is an autonomous revenue-recovery agent that turns failed payments into recoverable opportunities by detecting risk, diagnosing failures, selecting safe interventions, executing bounded recovery actions, verifying outcomes, and measuring the revenue actually recovered.**

---

# 🧠 The Big Idea

Traditional payment systems focus on:

```text
Did the payment succeed?
```

RecoverAI focuses on:

```text
The payment failed.

Why?

Can we recover it?

What's the safest action?

Should we act now?

Did it work?

How much money did we recover?

What should happen next?
```

That is the difference between a **payment-status dashboard** and an **autonomous revenue-recovery system**.

---

# 🔗 Important Official Resources

### Razorpay

[Razorpay Documentation](https://razorpay.com/docs/?utm_source=chatgpt.com)

[Razorpay Payments API](https://razorpay.com/docs/api/payments/?utm_source=chatgpt.com)

[Razorpay Webhooks](https://razorpay.com/docs/webhooks/?utm_source=chatgpt.com)

[Razorpay Payment Webhook Events](https://razorpay.com/docs/webhooks/payments/?utm_source=chatgpt.com)

[Razorpay Webhook Setup](https://razorpay.com/docs/payments/dashboard/account-settings/webhooks/?utm_source=chatgpt.com)

---

### Supabase

[Supabase Documentation](https://supabase.com/docs?utm_source=chatgpt.com)

[Supabase Database Documentation](https://supabase.com/docs/guides/database/overview?utm_source=chatgpt.com)

[Supabase PostgreSQL Connection Guide](https://supabase.com/docs/guides/database/connecting-to-postgres?utm_source=chatgpt.com)

---

### Render

[Render Documentation](https://render.com/docs?utm_source=chatgpt.com)

[Deploy FastAPI on Render](https://render.com/docs/deploy-fastapi?utm_source=chatgpt.com)

---

# 👨‍💻 Repository

**RecoverAI — Autonomous Revenue Recovery**

GitHub:

[RecoverAI-Razorpay GitHub Repository](https://github.com/vanshnain-builds/RecoverAI-Razorpay?utm_source=chatgpt.com)

---

# ❤️ Final Pitch

**RecoverAI doesn't just tell merchants that revenue was lost.**

It finds the revenue that can still be recovered.

It understands the reason behind the failure, evaluates the recovery opportunity, selects an appropriate intervention, validates that intervention against safety policies, executes the recovery workflow, verifies the result, and records the complete decision trail.

The result is a closed-loop system:

```text
                 ┌──────────────┐
                 │    Detect    │
                 └──────┬───────┘
                        ↓
                 ┌──────────────┐
                 │   Diagnose   │
                 └──────┬───────┘
                        ↓
                 ┌──────────────┐
                 │    Decide    │
                 └──────┬───────┘
                        ↓
                 ┌──────────────┐
                 │    Policy    │
                 └──────┬───────┘
                        ↓
                 ┌──────────────┐
                 │    Execute   │
                 └──────┬───────┘
                        ↓
                 ┌──────────────┐
                 │    Verify    │
                 └──────┬───────┘
                        ↓
                 ┌──────────────┐
                 │    Measure   │
                 └──────┬───────┘
                        ↓
                 💰 RECOVERED REVENUE
```

> **RecoverAI — Detect the leakage. Understand the failure. Recover the revenue.**

[1]: https://razorpay.com/docs/webhooks/?utm_source=chatgpt.com "About Webhooks | Razorpay Docs"
[2]: https://razorpay.com/docs/api/payments/?utm_source=chatgpt.com "Razorpay Docs"
[3]: https://razorpay.com/docs/payments/dashboard/account-settings/webhooks/?preferred-country=IN&utm_source=chatgpt.com "Webhooks | Razorpay Docs"
[4]: https://razorpay.com/docs/webhooks/payments/?utm_source=chatgpt.com "Payments Webhook Events | Razorpay Docs"
[5]: https://razorpay.com/docs/payments/quickstart/?utm_source=chatgpt.com "Quickstart Guide | Razorpay Docs"
[6]: https://supabase.com/docs/guides/database/overview?utm_source=chatgpt.com "Database | Supabase Docs"
[7]: https://render.com/docs/deploy-fastapi?utm_source=chatgpt.com "Deploy a FastAPI App – Render Docs"
[8]: https://render.com/docs/your-first-deploy?utm_source=chatgpt.com "Your First Render Deploy – Render Docs"
[9]: https://razorpay.com/docs/webhooks/validate-test/?preferred-country=IN&utm_source=chatgpt.com "Validate and Test Webhooks | Razorpay Docs"
