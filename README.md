# RecoverAI — Autonomous Revenue Recovery Agent

An AI agent that takes responsibility for recovering failed-payment revenue for
Razorpay merchants. It **detects** revenue slipping away, **diagnoses** why each
payment failed, **decides** the highest expected-value safe action, **executes**
it inside deterministic financial guardrails, and **measures the money it
actually recovers**.

> Every failed payment is different. RecoverAI investigates each case and takes
> the highest-value *safe* intervention — and knows when **not** to act.

---

## The agentic loop

```
RAZORPAY DATA → Revenue Monitor → Diagnostic Agent → Recovery Agent
             → Policy / Guard → Action Executor → Outcome Tracker → ₹ RECOVERED
```

- **Recovery Agent** (`app/agent.py`) — reasons: diagnosis (category, confidence,
  evidence) and decision (action, recovery probability, expected value, "why").
- **Policy Engine** (`app/policy.py`) — **no AI**. Deterministic retry / window /
  reminder / high-value-approval / risk rules. The safety boundary.
- **Action Executor** (`app/executor.py`) — the only layer that "acts". Computes
  recovered ₹ deterministically and handles failure safely (no endless retries,
  state preserved, next window queued). Actions run against a mock simulator by
  default; with Razorpay configured, `send_payment_link` creates a **real**
  (test-mode) payment link (see *Go real* below).
- **Engine** (`app/engine.py`) — orchestrates the loop, holds state, computes
  metrics and the prioritised recovery queue. Loads from real Razorpay when
  configured, else the seeded synthetic dataset (`app/source.py`), and mirrors
  everything to Supabase when configured (`app/store.py`).

**AI judgment, by design:** the model reasons and explains; deterministic code
enforces limits and counts money. We deliberately don't use AI where plain rules
are safer.

---

## Requirements

- **Python 3.10 – 3.14** (tested through 3.14). Dependency floors are pinned so a
  clean `pip install` pulls **prebuilt wheels only** — no Rust toolchain and no
  MSVC / `link.exe` needed, even on Python 3.14. See `backend/requirements.txt`.
- **Node.js ≥ 18** (only for the optional React frontend — Option B below).
- **No accounts or keys required to run the demo.** The Razorpay and Supabase
  integrations are optional and **off unless you provide keys** (see *Go real*
  below). Their libraries (`razorpay`, `requests`, `python-dotenv`) are pure-Python
  wheels included in `requirements.txt` and are imported lazily, so a keyless
  install still runs fully on synthetic data with in-memory state.

## Quick start

### 1. Backend (required)

```bash
cd backend
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Backend is now at `http://localhost:8000` — open it in a browser for the landing
page, `/docs` for interactive API docs, `/api/health` to confirm it's up.

> **Windows / Python 3.14 note.** If an *older* checkout ever fails building
> `pydantic-core` with `error: linker 'link.exe' not found`, you're on the old
> pins (`pydantic==2.9.2`). This project uses `pydantic>=2.11`, which ships
> Python 3.14 wheels, so no build tools are required. Using `python -m pip` /
> `python -m uvicorn` (rather than the bare `pip` / `uvicorn` shims) also avoids
> PATH issues on Windows.

### 2. Frontend — pick one

**Option A — zero install (fastest for a demo).** Just open `demo.html` in a
browser. It talks to the backend at `http://localhost:8000`. Single file, no
build step.

**Option B — full React app.**

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api → :8000)
```

Or use the launcher: `bash run.sh`.

> **`npm run dev` says `'vite' is not recognized`?** That happens when the build
> tooling lands in `devDependencies` and the install skips dev deps
> (`NODE_ENV=production`, `npm install --omit=dev`, or a locked-down corporate
> npm). This project keeps `vite` and `@vitejs/plugin-react` in **`dependencies`**
> so a clean `npm install` always installs them. The bundled `frontend/.npmrc`
> also sets `ignore-scripts=false` so esbuild's postinstall (the
> `esbuild@… postinstall: node install.js` step) can set up its platform binary.
> If in doubt, run a truly clean install: `rm -rf node_modules package-lock.json && npm install`.

---

## Verify the full stack locally

Run these after a **clean** checkout to confirm everything works end to end.

**Backend (fresh install → serve → smoke-test the loop):**

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Then, in a second terminal:

```bash
curl http://localhost:8000/api/health         # {"status":"ok",...}
curl http://localhost:8000/api/metrics         # revenue_at_risk / recoverable / recovered
curl -X POST http://localhost:8000/api/recover-batch   # agent works the batch; returns ₹ recovered + actions
curl http://localhost:8000/api/audit           # timestamped audit trail
```

Also open `http://localhost:8000/` (landing page — no longer a 404) and
`http://localhost:8000/docs` (interactive API).

**Frontend (clean install → dev server):**

```bash
cd frontend
rm -rf node_modules package-lock.json     # ensure a truly clean install
npm install                                # installs vite via dependencies; esbuild postinstall runs
npm run dev                                # serves http://localhost:5173, proxies /api → :8000
```

Open `http://localhost:5173` with the backend running. (No Node? Just open
`demo.html` — Option A above.)

---

## Go real: Razorpay (test mode) + Supabase

Everything above runs with **zero configuration** on synthetic data. To make it
operate on **real Razorpay data** and **persist to Supabase**, add a `.env` file —
no code changes. Each integration turns on independently and **falls back
gracefully** if a key is missing or a call fails, so the demo never breaks.

```bash
cd backend
cp .env.example .env       # Windows: copy .env.example .env
# then edit .env and fill in the values below
```

`.env` is gitignored — your keys never get committed, and they are read from the
environment, never hard-coded. **Use TEST keys only** (`rzp_test_…`).

### A. Ingest real Razorpay payments + create real payment links

In `.env`:

```
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
RAZORPAY_MODE=test
RECOVERAI_NOTIFY=0                 # 0 = never SMS/email a real person (safe default)
RECOVERAI_SIMULATE_COMPLETION=0    # 0 = count recovery only after a Razorpay webhook; 1 = demo simulation
RAZORPAY_WEBHOOK_SECRET=...        # secret configured for the Razorpay webhook endpoint
```

Get test keys from the Razorpay Dashboard → **Settings → API Keys → Generate Test
Key**. Restart the backend. On boot you'll see a log line like
`Loaded N Razorpay payments (M failed) in test mode`, and `/api/health` reports
`"data_source":"razorpay"`. The UI header shows a **● Live Razorpay (test)** badge.

- **Ingest** pulls a recent window (`RAZORPAY_FETCH_DAYS`, default 90; up to
  `RAZORPAY_FETCH_COUNT`, max 100) via the Fetch Payments API, maps Razorpay error
  reasons onto our failure categories, and derives per-customer history from the
  window. If Razorpay returns **no failed payments** in the window, it logs why and
  falls back to synthetic data (create a few failed test payments to see real data).
- **Payment links** are the one **real side effect**: when the agent's chosen
  action is `send_payment_link`, it calls the Payment Links API and puts the real
  `short_url` in the audit trail. `retry_payment` and all other actions stay
  simulated. Link *creation* is real; link *completion* (the customer paying) can
  only be confirmed by a webhook — hence `RECOVERAI_SIMULATE_COMPLETION`: leave it
  `1` for a self-contained demo (completion is simulated so ₹-recovered still moves),
  or set `0` to mark real links as **PENDING** and never count them as recovered
  until a webhook confirms. `RECOVERAI_NOTIFY=0` guarantees no real person is messaged.

### B. Persist to Supabase

1. Create a project at [supabase.com](https://supabase.com).
2. **SQL Editor → New query** → paste `db/supabase_schema.sql` → **Run** (safe to
   re-run). This creates the tables, enums, and views.
3. In `.env`:

```
SUPABASE_URL=https://<your-ref>.supabase.co        # Project Settings → API → Project URL
SUPABASE_SERVICE_KEY=<service_role secret>          # Project Settings → API → service_role
```

Restart the backend. `/api/health` reports `"persistence":"supabase"` and the UI
shows a **◆ Supabase** badge. State is written through the **PostgREST REST API**
(no native Postgres driver needed): the payment universe is upserted on load, and
every diagnosis, decision, policy evaluation, outcome, and audit entry is written as
the agent works. Writes are best-effort — a persistence error is logged and swallowed
so it can never break the recovery loop. The `service_role` key bypasses RLS and is
**server-side only** — never ship it to a browser.

### Verify the real integrations

```bash
curl http://localhost:8000/api/health
# → data_source: "razorpay", razorpay_mode: "test", persistence: "supabase", payments_loaded: N
curl -X POST http://localhost:8000/api/recover-batch     # works real failures; creates real links
```

Then, in Supabase → **Table editor**, confirm rows land in `payments`, `diagnoses`,
`decisions`, `outcomes`, and `audit_log` (or query the `recovery_metrics` view).
With no keys set, the same endpoints return `data_source:"synthetic"` /
`persistence:"memory"` — proof the fallback is intact.

---

## Optional: real LLM (hybrid)

The reasoning engine is **simulated by default** so the demo always runs with no
key and no network. To route diagnosis/decisions through a real model instead
(with automatic fallback to the simulator on any error):

```bash
export RECOVERAI_USE_LLM=1
export ANTHROPIC_API_KEY=...        # or OPENAI_API_KEY=...
# optional: export RECOVERAI_LLM_MODEL=claude-3-5-sonnet-latest
```

Prompts and the output-coercion logic live in `app/llm_adapter.py`.

---

## Demo script (7 scenes)

1. **Problem** — open the Command Center: revenue at risk vs recoverable vs recovered.
2. **Detection** — failed payments diagnosed and categorised.
3. **Investigation** — open a payment; show diagnosis, evidence, decision, and **Why?**.
4. **Execute** — click *Recover this payment*; watch the audit trail and ₹ recovered.
5. **Batch** — *Recover eligible payments*; the agent works the whole batch by priority.
6. **Failure** — on any payment, *Simulate API failure*; show safe failure handling.
7. **Audit** — the Audit Trail tab shows every action, timestamped.

Reset anytime with the **Reset demo** button (deterministic seed → same numbers).

---

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness + wiring status (data source, persistence, reasoning) |
| GET | `/api/metrics` | Headline money metrics |
| GET | `/api/pipeline` | Funnel counts (failed→recovered) |
| GET | `/api/categories` | Failure-category breakdown |
| GET | `/api/queue` | Prioritised recovery queue |
| GET | `/api/payments?status=failed` | List payments |
| GET | `/api/payments/{id}` | Diagnosis + decision + policy |
| POST | `/api/payments/{id}/recover` | Execute one (`{"force_failure": bool}`) |
| POST | `/api/recover-batch` | Recover all eligible, by priority |
| POST | `/api/webhooks/razorpay` | Verify Razorpay webhook and confirm recovered payment-link revenue |
| GET | `/api/audit` | Full action audit trail |
| POST | `/api/chat` | Natural-language front door |
| POST | `/api/reset` | Reset to initial deterministic state |

See `BLUEPRINT.md` for data schema, policy rules, agent prompts, and the 48-hour
build sequence.

---

## Database

**There is no external database by default — and that's intentional.** The engine
holds all state in memory and rebuilds it from a **seeded** synthetic Razorpay
dataset (`app/dataset.py`, `seed=42`) on every start. That's what makes the demo
reproducible: the same revenue-at-risk and ₹-recovered numbers every run, and a
one-click **Reset** (`POST /api/reset`). Nothing to provision to evaluate it.

When you want to **persist** payments, diagnoses, decisions, policy evaluations,
outcomes, and the audit log, a ready-to-run PostgreSQL schema is included at
**`db/supabase_schema.sql`**. It mirrors the shapes in `app/models.py` and adds
two convenience views (`recovery_records`, `recovery_metrics`).

Persistence is **already wired** (write-through via the Supabase PostgREST REST
API in `app/store.py`) and turns on automatically once `SUPABASE_URL` and
`SUPABASE_SERVICE_KEY` are set — see **Go real → B. Persist to Supabase** above for
the step-by-step. With no keys set, the engine simply stays in memory. Either way
the in-memory engine remains the source of truth at runtime, so the demo stays fast
and reproducible; Supabase receives a mirror of the same state.

---

## Layout

```
recoverai/
├── backend/
│   ├── requirements.txt      # pinned for prebuilt wheels (Py 3.10–3.14)
│   ├── .env.example          # copy to .env for real Razorpay/Supabase (gitignored)
│   └── app/
│       ├── models.py        # Pydantic shapes + enums
│       ├── config.py        # env-based config + feature toggles (reads .env)
│       ├── dataset.py       # synthetic Razorpay dataset (seeded)
│       ├── source.py        # picks real Razorpay vs synthetic, with fallback
│       ├── razorpay_client.py # Razorpay ingest + real payment links (test mode)
│       ├── store.py         # Supabase write-through via PostgREST (optional)
│       ├── agent.py         # diagnose / decide (simulated + LLM hybrid)
│       ├── llm_adapter.py   # optional real-LLM adapter + prompts
│       ├── policy.py        # deterministic guardrails (no AI)
│       ├── executor.py      # action executor + safe failure handling
│       ├── engine.py        # orchestration + metrics + queue
│       ├── chat.py          # conversational interface
│       └── main.py          # FastAPI app (+ landing page, optional /app build)
├── frontend/                # React + Vite UI
│   ├── .npmrc               # ignore-scripts=false (esbuild postinstall)
│   ├── package.json         # vite in dependencies (clean-install safe)
│   └── src/ (App + components)
├── db/
│   └── supabase_schema.sql  # optional Postgres/Supabase persistence
├── demo.html                # zero-install fallback UI
├── run.sh                   # launcher
├── README.md
└── BLUEPRINT.md             # full implementation blueprint
```


## Reset Demo and metrics
Reset Demo restores the exact payment dataset loaded when the backend started, clears diagnoses/decisions/policies/outcomes and clears the in-memory audit trail. It does not delete historical Supabase audit rows.

Dashboard metrics are defined as: At risk = original failed-payment revenue; Recoverable = AI-identified opportunity; Recovered = successful/verified recovery amount; Remaining recoverable = recoverable opportunity still outstanding.

## Razorpay keys
Copy `backend/.env.example` to `backend/.env` and replace `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET` with your Razorpay TEST credentials. Keep `backend/.env` out of Git. Set `RECOVERAI_SIMULATE_COMPLETION=0` when you want real Payment Link completion to be counted only after a verified Razorpay webhook.
