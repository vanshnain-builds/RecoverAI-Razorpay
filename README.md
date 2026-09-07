# 🤖 RecoverAI

### Autonomous AI-Powered Revenue Recovery

<p>
  <img src="https://img.shields.io/badge/Razorpay-Hackathon-0C2451?style=for-the-badge&logo=razorpay&logoColor=white" alt="Razorpay Hackathon"/>
  <img src="https://img.shields.io/badge/React-Frontend-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React"/>
  <img src="https://img.shields.io/badge/Python-Backend-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Supabase-Database-3ECF8E?style=for-the-badge&logo=supabase&logoColor=black" alt="Supabase"/>
</p>

> **Detect revenue at risk → Diagnose → Decide → Recover → Verify → Measure**

## 🌐 Live Demo

### 🚀 Try RecoverAI

#### 👉 [RecoverAI Live Application](https://YOUR-FRONTEND-URL.onrender.com)

#### 👉 [Backend API](https://recoverai-razorpay-1.onrender.com)

#### 👉 [API Documentation](https://recoverai-razorpay-1.onrender.com/docs)

> 💡 **For judges:** Open the Live Application above to experience the RecoverAI dashboard and recovery workflow.

---

## 📌 Project Overview

> An AI-powered revenue recovery system that finds failed payments, understands why they failed, chooses the best recovery action, executes it safely, and tracks how much revenue was recovered.

## 🚀 What is RecoverAI?

RecoverAI is our solution for the **AI Revenue Recovery** track of the Razorpay Hackathon.

The basic problem we focused on is simple: when a payment fails, the merchant loses potential revenue. But not every failed payment should be treated in the same way.

For example, a temporary network failure may be worth retrying, while a payment-method issue may need a different approach. A customer who has successfully paid many times before may also be a better recovery opportunity than a completely new customer.

RecoverAI tries to automate this decision-making process.

Instead of just showing a list of failed payments, the system goes through the complete recovery flow:

**Detect → Diagnose → Decide → Validate → Execute → Measure**

The goal is to help a merchant recover more money while keeping the recovery process controlled, explainable and auditable.

---

# 🎯 Problem We Are Solving

Failed payments are not always permanent losses.

A merchant can have revenue slipping away because of:

- Temporary bank or network failures
- Payment method problems
- Customer-side actions
- Failed subscription payments
- Checkout/payment drop-offs
- Other payment failures

The difficult part is not only detecting that a payment failed.

The real question is:

> **"What should we do about this failed payment?"**

Should we retry it?

Should we ask the customer to try another payment method?

Should we wait and retry later?

Should we escalate it?

And most importantly:

> **Which failed payment should we try to recover first?**

RecoverAI is designed to answer these questions automatically.

---

# 💡 Our Solution

RecoverAI treats revenue recovery as a decision-making problem.

For every failed payment, the system looks at the available information and creates a recovery decision.

It considers things such as:

- Payment amount
- Failure reason
- Payment method
- Previous customer payment history
- Previous retry attempts
- Risk information
- Failure category
- Estimated probability of successful recovery

Based on this information, RecoverAI recommends a suitable recovery action.

The system then applies a policy check before executing the action.

This gives us a complete chain:

```text
Failed Payment
      ↓
Detect
      ↓
Diagnose Failure
      ↓
Estimate Recovery Probability
      ↓
Choose Recovery Action
      ↓
Policy Validation
      ↓
Execute Recovery
      ↓
Success / Failure / Pending
      ↓
Update Metrics + Audit Trail

---

# 🧠 What Makes RecoverAI Different?

A normal payment dashboard might tell a merchant:

> "156 payments failed."

RecoverAI tries to go one step further:

> "These payments failed, this is why they probably failed, these are the ones worth recovering, this is the recommended action, this is the expected recovery value, and this is what happened after the action."

So the focus is not just **payment monitoring**.

It is **autonomous revenue recovery**.

---

# 🏗️ How RecoverAI Works

## 1. Detect

The system first identifies failed payments.

Each payment contains information that can be used for analysis.

Example:

```text
Payment: RZP-10014
Amount: ₹2,999
Method: Card
Failure: network_error
Previous successful payments: 10
Retry count: 0
```

---

## 2. Diagnose

RecoverAI analyzes the payment failure and tries to understand its category.

For example:

```text
network_error
      ↓
Temporary failure
```

The diagnosis also includes a confidence score.

For example:

```text
Diagnosis: Temporary failure
Confidence: 87%
```

This allows the system to explain why a particular recovery action was selected.

---

## 3. Decide

After diagnosing the failure, RecoverAI calculates whether the payment looks worth recovering.

It estimates:

**P(recover)**

and:

**Expected Recovery = Payment Amount × Recovery Probability**

For example:

```text
Payment amount:       ₹2,999
Recovery probability: 91%

Expected recovery:
₹2,999 × 0.91 ≈ ₹2,729
```

This helps the system prioritize recovery opportunities.

---

# 📊 Recovery Queue

RecoverAI does not simply process failed payments randomly.

The Recovery Queue is ordered using the expected recovered value, while considering risk and operational effort.

For example:

```text
Payment       Amount       p(recover)       Expected ₹
-------------------------------------------------------
RZP-10014     ₹2,999          91%              ₹2,729
RZP-10021     ₹4,500          72%              ₹3,240
RZP-10037     ₹1,800          80%              ₹1,440
```

This means the agent can decide:

> **What should I recover first?**

rather than only:

> **Is this payment recoverable?**

---

# 🤖 AI Agent

The AI part of RecoverAI is responsible for helping with the recovery decision.

The agent follows a structured process rather than blindly executing an action.

### Agent flow

```text
Observe
   ↓
Understand the payment
   ↓
Diagnose the failure
   ↓
Evaluate recovery opportunity
   ↓
Select an action
   ↓
Check policy
   ↓
Execute
   ↓
Observe result
   ↓
Record outcome
```

This is important because an autonomous system should not simply call an API and hope for the best.

It needs to know:

* What happened?
* Why did it happen?
* What action makes sense?
* Is that action allowed?
* What happened after execution?

---

# 🔐 Safe Recovery With Policy Checks

We added a policy layer before recovery actions are executed.

The idea is that the AI should have boundaries.

For example, the system can check:

* Whether the payment is eligible for recovery
* Whether the retry limit has been reached
* Whether the selected action is allowed
* Whether the operation is considered safe
* Whether additional escalation is required

The recovery flow therefore becomes:

```text
AI Recommendation
       ↓
Policy Validation
       ↓
Allowed?
   ↙       ↘
 YES       NO
 ↓          ↓
Execute    Stop / Escalate
```

This prevents the AI from becoming an uncontrolled automation system.

---

# 💳 Recovery Actions

Depending on the payment situation, the system can recommend recovery actions such as:

### Retry Payment

Useful for temporary failures such as network or transient bank issues.

### Payment Method Recovery

Used when the current payment method may be the problem.

### Subscription Recovery

Used for failed subscription-related payments.

### Customer Action

Used when the customer needs to take an action to complete the payment.

The important part is that the system does not assume that one recovery action works for every failure.

---

# 📈 Metrics

The dashboard clearly separates different revenue states.

## At Risk

The original amount associated with failed payments.

This represents the revenue that is currently at risk.

## Recoverable

The amount that RecoverAI identifies as a realistic recovery opportunity based on its recovery logic and threshold.

## Recovered

The amount from recovery actions that were successfully completed and verified.

## Remaining

Recoverable revenue that has not yet been successfully recovered.

The relationship is approximately:

```text
At Risk
   ↓
Recoverable
   ↓
 ┌───────────────┐
 ↓               ↓
Recovered     Remaining
```

This makes the dashboard easier for a merchant to understand.

---

# 📊 Dashboard

The Command Center provides a quick overview of the current recovery situation.

It shows metrics such as:

* At-risk revenue
* Recoverable revenue
* Recovered revenue
* Remaining recoverable revenue
* Failed payments
* Recovery rate
* Number of recovery actions taken

It also shows the recovery pipeline and failure categories.

---

# 🔎 Investigation Page

The Investigation page allows the merchant to look at an individual payment in more detail.

For a payment, the merchant can see:

* Payment amount
* Payment method
* Failure code
* Customer payment history
* Preferred payment method
* Retry count
* Risk score
* AI diagnosis
* Recovery probability
* Recommended action
* Expected recovery value

For example:

```text
Payment: RZP-10014

Amount: ₹2,999
Failure: network_error

AI Diagnosis:
Temporary bank/payment network failure

Confidence:
87%

Recovery probability:
91%

Recommended action:
retry_payment

Expected recovery:
₹2,729
```

This makes the AI decision explainable instead of just showing a result.

---

# ⚡ Recovery Execution

The merchant can execute a recommended recovery action directly from the Investigation page.

After execution, RecoverAI records the result.

Possible outcomes include:

```text
SUCCESS
FAILURE
PENDING
```

### Success

The payment was successfully recovered.

### Failure

The recovery attempt did not succeed.

### Pending

The recovery process has been initiated but the final result is not available yet.

The UI updates the payment state accordingly.

---

# 🧾 Audit Trail

Every important step is recorded in the Audit Trail.

For example:

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

An example could look like:

```text
Payment failure detected

Diagnosed as temporary_failure
Confidence: 87%

Selected action: retry_payment
Recovery probability: 91%

Policy validation: PASSED

Recovery initiated via retry_payment

Payment successful
₹2,999 recovered
```

This gives the merchant visibility into what the system did.

It also makes the autonomous process easier to debug and review.

---

# 💬 Ask RecoverAI

RecoverAI also includes an AI chat interface.

A merchant can ask questions about the recovery data instead of manually going through every table.

For example:

```text
Which payments should I recover first?

Why is this payment considered recoverable?

How much revenue is still at risk?

Which failure category has the highest amount?

Why did the agent choose retry_payment?
```

The goal is to make the recovery system easier to interact with.

---

# 🗄️ Supabase

We use **Supabase** as the database layer.

The project can store information such as:

* Payments
* Recovery decisions
* Recovery outcomes
* Audit events
* Recovery-related data

The database schema is included in:

```text
db/supabase_schema.sql
```

The backend connects to Supabase through environment variables rather than hardcoding credentials.

---

# 💳 Razorpay Integration

RecoverAI is designed around the Razorpay payment/revenue recovery workflow.

For development and demonstration, the project also supports **synthetic payment data**.

This is intentional because it allows us to demonstrate the complete recovery workflow without depending entirely on live customer payments.

The architecture allows Razorpay data to enter through backend integrations/webhooks and then pass through the same recovery pipeline.

```text
Razorpay
   ↓
Webhook / API
   ↓
RecoverAI Backend
   ↓
Diagnosis
   ↓
Recovery Decision
   ↓
Policy
   ↓
Recovery Action
   ↓
Database
   ↓
Dashboard
```

---

# 🔔 Webhooks

For a production version, payment events can be sent to RecoverAI using Razorpay webhooks.

For example, when a payment event occurs:

```text
Razorpay
   ↓
Webhook
   ↓
/api/webhooks/razorpay
   ↓
Validate event
   ↓
Store/update payment
   ↓
Run recovery analysis
```

This allows RecoverAI to react to payment events instead of requiring the merchant to manually refresh the dashboard.

Webhook secrets and API credentials should be stored as environment variables.

---

# 🏛️ System Architecture

```text
                    ┌──────────────────────┐
                    │       Razorpay       │
                    │  Payments / Events   │
                    └──────────┬───────────┘
                               │
                         API / Webhook
                               │
                               ▼
                    ┌──────────────────────┐
                    │   RecoverAI Backend  │
                    │       FastAPI        │
                    └──────────┬───────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
          Detection       AI Diagnosis    Policy Engine
                │              │              │
                └──────────────┼──────────────┘
                               ▼
                       Recovery Decision
                               │
                               ▼
                       Recovery Executor
                               │
                    ┌──────────┴───────────┐
                    │                      │
                    ▼                      ▼
              Recovery Result        Audit Trail
                    │                      │
                    └──────────┬───────────┘
                               ▼
                         Supabase DB
                               │
                               ▼
                    ┌──────────────────────┐
                    │    React Frontend    │
                    │     Dashboard        │
                    └──────────────────────┘
```

---

# 🧰 Tech Stack

### Frontend

* React
* Vite
* JavaScript
* CSS

### Backend

* Python
* FastAPI
* Pydantic

### Database

* Supabase
* PostgreSQL

### AI

* LLM-based decision support
* Rule/policy layer
* Recovery scoring

### Payment Platform

* Razorpay APIs
* Razorpay Webhooks

### Deployment

* Frontend: Vercel / similar frontend hosting
* Backend: Render
* Database: Supabase

---

# 📁 Project Structure

```text
RecoverAI-Razorpay/
│
├── backend/
│   ├── app/
│   │   ├── agent.py
│   │   ├── chat.py
│   │   ├── config.py
│   │   ├── dataset.py
│   │   ├── engine.py
│   │   ├── executor.py
│   │   ├── llm_adapter.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── policy.py
│   │   ├── razorpay_client.py
│   │   ├── source.py
│   │   └── store.py
│   │
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AuditTrail.jsx
│   │   │   ├── Chat.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Investigation.jsx
│   │   │   └── Queue.jsx
│   │   │
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── main.jsx
│   │   └── styles.css
│   │
│   ├── package.json
│   └── vite.config.js
│
├── db/
│   └── supabase_schema.sql
│
├── demo.html
├── BLUEPRINT.md
├── README.md
├── run.sh
└── .gitignore
```

---

# 🖥️ Screenshots

## Command Center

The main dashboard gives the merchant an overview of the revenue recovery situation.

<img width="1917" height="905" alt="image" src="https://github.com/user-attachments/assets/709308f8-2570-42d3-b5dd-dea5323541a1" />
<img width="1917" height="910" alt="image" src="https://github.com/user-attachments/assets/0427886b-e872-48d0-a51b-4111e7d94c3d" />



---

## Recovery Queue

The queue ranks recovery opportunities by expected recovered value.

<img width="1917" height="903" alt="image" src="https://github.com/user-attachments/assets/b6d7c330-d5d1-42f2-8a6c-b4277e3f7900" />
<img width="1917" height="901" alt="image" src="https://github.com/user-attachments/assets/f690f972-5f05-4345-8047-e88325c1c5a7" />



---

## Investigation

The Investigation page explains an individual payment and the AI's recovery decision.

<img width="1917" height="911" alt="image" src="https://github.com/user-attachments/assets/7adcd01b-39e3-438e-85ce-feca3e39f701" />
<img width="1917" height="895" alt="image" src="https://github.com/user-attachments/assets/f160ff30-f5f1-4383-ba5a-f83591e69906" />
<img width="1917" height="910" alt="image" src="https://github.com/user-attachments/assets/2dfeab17-6971-476c-a043-bcc21c1096e9" />





---

## Audit Trail

The Audit Trail shows what happened at every stage of the recovery process.

<img width="1917" height="903" alt="image" src="https://github.com/user-attachments/assets/21b8f39f-c60d-4b26-9330-00b1cf27ede3" />
<img width="1917" height="902" alt="image" src="https://github.com/user-attachments/assets/c5f334d6-2c3e-49cc-a3f4-2d9ff50754e9" />



---

## Ask RecoverAI

The chat interface allows merchants to ask questions about their recovery data.

<img width="1917" height="908" alt="image" src="https://github.com/user-attachments/assets/8dfac23f-aaa4-43ed-8f1e-54c52ca410ec" />


---

# 🔄 Demo Flow

The easiest way to understand RecoverAI is to follow one payment.

### Step 1 — Failed payment appears

A payment fails because of a particular failure reason.

### Step 2 — RecoverAI diagnoses it

The system analyzes the available payment and customer information.

### Step 3 — Recovery probability is calculated

RecoverAI estimates the likelihood of recovering the payment.

### Step 4 — Recovery action is selected

The system chooses an appropriate action.

For example:

```text
retry_payment
```

### Step 5 — Policy validation

Before execution, the action is checked against the recovery policy.

### Step 6 — Recovery is executed

The recovery action is initiated.

### Step 7 — Outcome is recorded

The payment becomes:

```text
Recovered
```

or:

```text
Failed
```

or:

```text
Pending
```

### Step 8 — Metrics change

The dashboard reflects the new recovery result.

### Step 9 — Audit event is created

The entire action is recorded in the Audit Trail.

---

# 🔁 Reset Demo

The project includes a **Reset Demo** option.

This is useful during demonstrations because the dataset can be restored to its original state before running the recovery flow again.

This allows judges to see the same end-to-end workflow repeatedly without manually rebuilding the demo data.

---

# 📊 Example Recovery Calculation

Suppose we have:

```text
Payment amount = ₹10,000
Recovery probability = 80%
```

The expected recovery is:

```text
₹10,000 × 0.80
= ₹8,000
```

If another payment has:

```text
Payment amount = ₹5,000
Recovery probability = 95%
```

Its expected recovery is:

```text
₹5,000 × 0.95
= ₹4,750
```

RecoverAI can use this kind of calculation to help prioritize recovery opportunities.

The important idea is that **recovery priority is based on potential value, not simply payment amount.**

---

# 🧪 Synthetic Data

The demo uses synthetic payment data so that the complete recovery workflow can be demonstrated safely.

The synthetic dataset contains different types of failed payments with different characteristics.

This allows us to demonstrate scenarios such as:

* Temporary failures
* Customer action failures
* Payment method issues
* Subscription failures
* Unknown failures
* Different payment amounts
* Different customer histories
* Different recovery probabilities

The same processing pipeline can later work with real payment-event data.

---

# 🔒 Security Considerations

Sensitive credentials should never be committed to GitHub.

Use environment variables for:

```text
RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET
RAZORPAY_WEBHOOK_SECRET
SUPABASE_URL
SUPABASE_KEY
LLM_API_KEY
```

The repository should only contain an example environment file such as:

```text
backend/.env.example
```

Actual secrets should be configured in the deployment environment.

---

# ⚙️ Running Locally

## Backend

Go to the backend directory:

```bash
cd backend
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start FastAPI:

```bash
uvicorn app.main:app --reload
```

The backend should then be available locally.

---

## Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite development server will provide the frontend URL.

---

# 🌐 Deployment

The project can be split into three services:

```text
Frontend
   ↓
Vercel

Backend
   ↓
Render

Database
   ↓
Supabase
```

The frontend uses an environment variable for the backend URL.

Example:

```text
VITE_API_URL=https://your-backend.onrender.com
```

The backend contains the Supabase and Razorpay configuration through environment variables.

---

# 🌱 Environment Variables

Backend:

```text
SUPABASE_URL=
SUPABASE_KEY=

RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=

LLM_PROVIDER=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

Frontend:

```text
VITE_API_URL=
```

Do not put secret keys inside the frontend.

---

# 🧩 API Endpoints

Some of the main backend endpoints are:

```text
GET  /api/health
GET  /api/metrics
GET  /api/pipeline
GET  /api/categories
GET  /api/queue
GET  /api/payments
GET  /api/payments/{id}
POST /api/payments/{id}/recover
POST /api/recover-batch
GET  /api/audit
POST /api/chat
POST /api/reset
```

These APIs connect the frontend dashboard with the recovery engine.

---

# 🧠 Why AI Instead of Only Rules?

A pure rules-based system could say:

```text
if network_error:
    retry
```

But real payment recovery can involve multiple signals.

RecoverAI can consider:

```text
Failure reason
+
Customer history
+
Payment method
+
Retry history
+
Amount
+
Risk
+
Recovery probability
+
Policy constraints
```

This makes the decision more contextual.

The AI also provides a diagnosis and explanation that can be shown to the merchant.

At the same time, the policy layer provides boundaries around what can actually be executed.

---

# 🚧 Challenges We Faced

## 1. Connecting Frontend and Backend

One of the early problems was making the frontend communicate correctly with the deployed FastAPI backend.

The local development setup uses Vite's proxy, while the production frontend needs the deployed backend URL.

We solved this by using:

```text
VITE_API_URL
```

so the same frontend code can work in both development and production.

---

## 2. Backend Deployment

The backend initially worked locally but required configuration changes for cloud deployment.

Environment variables, the application start command, and the correct API URL had to be configured separately for the deployed environment.

---

## 3. Database Integration

Moving from in-memory demo data toward Supabase required separating the application logic from the storage layer.

This makes it easier to use the same recovery engine with persistent payment and audit data.

---

## 4. Recovery State Management

A recovery action cannot simply be treated as successful every time.

We needed to distinguish:

```text
Success
Failure
Pending
```

This makes the recovery metrics more realistic and prevents the dashboard from showing incorrect recovered revenue.

---

## 5. Safe Autonomous Actions

Giving an AI permission to execute payment-related actions without boundaries would be risky.

We therefore added a policy validation stage before execution.

The AI recommends the action, but the system checks whether the action is allowed before executing it.

---

# 💰 Business Value

The main value of RecoverAI is straightforward:

**recover revenue that might otherwise be lost.**

For a merchant with a large number of failed payments, even a small improvement in recovery rate can represent significant additional revenue.

RecoverAI also reduces the amount of manual work required to investigate failed payments.

Instead of manually checking every failed payment:

```text
Failed Payments
      ↓
AI prioritization
      ↓
Best opportunities first
      ↓
Recovery
      ↓
Measured revenue
```

This makes the recovery process more efficient.

---

# 📈 Scalability

The architecture is designed so that the system can move from a demo to a production workflow.

Instead of synthetic data:

```text
Razorpay events
```

can become the source.

Instead of in-memory storage:

```text
Supabase / PostgreSQL
```

can provide persistent storage.

Instead of manually triggering recovery:

```text
Webhooks + background jobs
```

can trigger the process automatically.

A production architecture could therefore look like:

```text
Razorpay
   ↓
Webhooks
   ↓
FastAPI
   ↓
Queue / Background Worker
   ↓
AI Recovery Engine
   ↓
Policy Engine
   ↓
Recovery Action
   ↓
Supabase
   ↓
Dashboard
```

---

# 🔮 Future Improvements

There are several areas where RecoverAI can be extended.

### Real-time Razorpay Events

Automatically process new payment events through webhooks.

### Better Recovery Models

Train a model using historical recovery outcomes to improve recovery probability estimates.

### Smarter Customer Segmentation

Use customer behavior and historical payment patterns to select more personalized recovery actions.

### Automated Retry Scheduling

Instead of immediately retrying every eligible payment, determine the best time for retrying.

### More Recovery Channels

The system could eventually coordinate:

* Payment retries
* Payment-method changes
* Customer notifications
* Subscription recovery
* Invoice follow-ups

### Advanced Analytics

Add dashboards showing:

* Recovery rate by failure type
* Recovery rate by payment method
* Revenue recovered over time
* Average recovery value
* Best-performing recovery actions
* Customer-level recovery trends

---

# 🎯 What We Built for the Hackathon

For this hackathon, our focus was not simply to build another payment dashboard.

We built a working concept around the complete revenue recovery loop:

```text
Detect
  ↓
Understand
  ↓
Decide
  ↓
Validate
  ↓
Execute
  ↓
Measure
```

The project demonstrates how an AI agent can move from identifying a revenue problem to taking a bounded action and measuring the result.

That is the main idea behind RecoverAI.

---

# 🏆 Why RecoverAI Fits the AI Revenue Recovery Track

The track asks teams to build an agent that can:

* Detect revenue at risk
* Determine the right intervention
* Execute a bounded recovery workflow
* Show measured money recovered
* Include stopping rules
* Maintain an audit trail

RecoverAI is built around exactly this workflow.

The system does not stop at:

```text
"Payment failed."
```

It continues through:

```text
Payment failed
      ↓
Why did it fail?
      ↓
Can it be recovered?
      ↓
What action should we take?
      ↓
Is the action allowed?
      ↓
Execute
      ↓
Did we recover the money?
      ↓
Record the result
```

This gives the project a complete recovery loop rather than only a prediction or analytics dashboard.

---

# 👥 Team

Built for the Razorpay Hackathon.

**Project:** RecoverAI
**Track:** AI Revenue Recovery

---

# 📚 References & Technologies

* [Razorpay](https://razorpay.com/)
* [Razorpay Documentation](https://razorpay.com/docs/)
* [Razorpay Webhooks](https://razorpay.com/docs/webhooks/)
* [Supabase](https://supabase.com/)
* [FastAPI](https://fastapi.tiangolo.com/)
* [React](https://react.dev/)
* [Vite](https://vite.dev/)
* [PostgreSQL](https://www.postgresql.org/)

---

# 📌 Final Summary

RecoverAI is an autonomous revenue recovery system built to help merchants turn failed payments into recoverable revenue.

It combines payment information, customer history, failure diagnosis, recovery probability, action selection, policy validation, execution, and outcome tracking into one workflow.

The key idea is simple:

> **Don't just tell the merchant that revenue was lost. Help recover it.**

```text
                    RECOVERAI

        Detect revenue at risk
                  ↓
          Diagnose the cause
                  ↓
       Estimate recovery chance
                  ↓
        Select best action
                  ↓
        Validate with policy
                  ↓
           Execute safely
                  ↓
        Measure the outcome
                  ↓
        Record audit trail
                  ↓
          Recover revenue
```
**RecoverAI — From failed payments to recovered revenue.**
