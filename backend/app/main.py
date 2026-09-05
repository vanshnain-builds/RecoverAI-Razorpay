"""FastAPI application — the RecoverAI backend.

Exposes the agentic loop over HTTP:
  GET  /                           -> service landing page (fixes bare GET / 404)
  GET  /api/health
  GET  /api/metrics
  GET  /api/pipeline
  GET  /api/categories
  GET  /api/queue
  GET  /api/payments
  GET  /api/payments/{id}          -> diagnosis + decision + policy
  POST /api/payments/{id}/recover  -> execute one (optional force_failure)
  POST /api/recover-batch          -> recover all eligible
  GET  /api/audit
  POST /api/chat
  POST /api/reset

If a production frontend build exists at ../frontend/dist (after `npm run build`),
it is served at /app so the whole product can run from this one process.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import chat as chat_mod
from . import config, razorpay_client
from .engine import get_engine

app = FastAPI(title="RecoverAI", version="1.0.0",
              description="Autonomous Revenue Recovery Agent for Razorpay merchants")

# The React dev server runs on a different port; allow it in dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Root / landing (previously a bare GET / returned 404)
# --------------------------------------------------------------------------- #
_ROOT_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>RecoverAI API</title>
<style>
 body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#0b0e14;color:#e6ebf2;
   max-width:720px;margin:60px auto;padding:0 20px;line-height:1.6}
 a{color:#3b82f6} code{background:#1c2330;padding:2px 6px;border-radius:5px}
 .card{background:#141925;border:1px solid #263041;border-radius:12px;padding:20px 24px}
 h1{margin-top:0} li{margin:4px 0}
</style></head>
<body><div class="card">
<h1>&#9670; RecoverAI API</h1>
<p>The backend is running. This is the API service; the merchant UI runs separately.</p>
<ul>
  <li>Interactive API docs: <a href="/docs">/docs</a></li>
  <li>Health check: <a href="/api/health">/api/health</a></li>
  <li>Razorpay webhook: <code>POST /api/webhooks/razorpay</code></li>
  <li>Headline metrics: <a href="/api/metrics">/api/metrics</a></li>
  <li>Recovery queue: <a href="/api/queue">/api/queue</a></li>
</ul>
<p><b>UI options</b></p>
<ul>
  <li>Zero-install: open <code>demo.html</code> from the project root in your browser.</li>
  <li>React dev server: <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run dev</code>
      then open <a href="http://localhost:5173">http://localhost:5173</a>.</li>
  <li>Production build served here: run <code>npm run build</code> in <code>frontend/</code>,
      restart this server, then open <a href="/app">/app</a>.</li>
</ul>
</div></body></html>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root():
    return _ROOT_HTML


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "RecoverAI", **get_engine().status()}


@app.get("/api/metrics")
def metrics():
    return get_engine().metrics()


@app.get("/api/pipeline")
def pipeline():
    return get_engine().pipeline()


@app.get("/api/categories")
def categories():
    return get_engine().category_breakdown()


@app.get("/api/queue")
def queue(limit: int = 25):
    return get_engine().queue(limit=limit)


@app.get("/api/payments")
def payments(status: str | None = None, limit: int = 100):
    return get_engine().list_payments(status=status, limit=limit)


@app.get("/api/payments/{payment_id}")
def payment_detail(payment_id: str):
    engine = get_engine()
    if payment_id not in engine.records:
        raise HTTPException(status_code=404, detail="payment not found")
    rec = engine.detail(payment_id)
    return rec.model_dump()


class RecoverBody(BaseModel):
    force_failure: bool = False


@app.post("/api/payments/{payment_id}/recover")
def recover_one(payment_id: str, body: RecoverBody | None = None):
    engine = get_engine()
    if payment_id not in engine.records:
        raise HTTPException(status_code=404, detail="payment not found")
    force = body.force_failure if body else False
    rec = engine.recover_one(payment_id, force_failure=force)
    return rec.model_dump()


@app.post("/api/recover-batch")
def recover_batch(limit: int | None = None):
    return get_engine().recover_batch(limit=limit)


@app.get("/api/audit")
def audit(limit: int = 200):
    entries = get_engine().global_audit[-limit:]
    return [e.model_dump() for e in entries]


@app.post("/api/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    """Receive verified Razorpay webhook events and confirm recovered revenue.

    Razorpay signs the raw request body with HMAC-SHA256. We verify it before
    parsing JSON, then handle payment_link.paid. Duplicate webhook deliveries
    are harmless because confirm_recovery is idempotent.
    """
    if not config.RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Razorpay webhook secret is not configured")

    raw = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not razorpay_client.verify_webhook_signature(raw, signature):
        raise HTTPException(status_code=401, detail="invalid Razorpay webhook signature")

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="invalid JSON payload") from exc

    event = payload.get("event", "")
    if event not in {"payment_link.paid", "payment.captured", "order.paid"}:
        return JSONResponse({"status": "ignored", "event": event})

    # Payment Link events contain the source_payment_id in the notes we set when
    # creating the link. Support the nested variants used by Razorpay events.
    candidates = [
        payload.get("payload", {}).get("payment_link", {}).get("entity", {}),
        payload.get("payload", {}).get("payment", {}).get("entity", {}),
        payload.get("payload", {}).get("order", {}).get("entity", {}),
    ]
    source_payment_id = None
    paid_amount = 0.0
    for entity in candidates:
        notes = entity.get("notes") or {}
        source_payment_id = notes.get("source_payment_id") or source_payment_id
        if not paid_amount:
            paid_amount = float(entity.get("amount_paid") or entity.get("amount_captured") or entity.get("amount") or 0) / 100.0

    if not source_payment_id:
        return JSONResponse({"status": "ignored", "event": event, "reason": "source_payment_id missing"})

    engine = get_engine()
    if source_payment_id not in engine.records:
        raise HTTPException(status_code=404, detail="source payment not found")

    engine.confirm_recovery(source_payment_id, paid_amount, source="razorpay_webhook")
    return {"status": "processed", "event": event, "payment_id": source_payment_id, "recovered_amount": paid_amount}


class ChatBody(BaseModel):
    message: str


@app.post("/api/chat")
def chat(body: ChatBody):
    return chat_mod.handle(get_engine(), body.message)


@app.post("/api/reset")
def reset():
    engine = get_engine()
    engine.reset()
    return {"status": "reset", "metrics": engine.metrics()}


# --------------------------------------------------------------------------- #
# Optionally serve a production frontend build at /app (present after
# `npm run build` in frontend/). Mounted last so it never shadows /api or /docs.
# --------------------------------------------------------------------------- #
_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/app", StaticFiles(directory=str(_dist), html=True), name="frontend")
