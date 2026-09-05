import React, { useEffect, useState } from "react";
import { api, rupees, pct } from "../api.js";

function PaymentPicker({ onPick }) {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    api.payments("failed").then((r) => setRows(r.slice(0, 40))).catch(() => {});
  }, []);
  return (
    <div className="card">
      <h3>Pick a failed payment to investigate</h3>
      <table>
        <thead>
          <tr>
            <th>Payment</th>
            <th className="right">Amount</th>
            <th>Method</th>
            <th>Failure code</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.payment_id} className="clickable" onClick={() => onPick(r.payment_id)}>
              <td className="mono">{r.payment_id}</td>
              <td className="right mono">{rupees(r.amount)}</td>
              <td>{r.payment_method}</td>
              <td className="mono">{r.failure_code}</td>
              <td>
                <span className={`pill ${r.final_status}`}>{r.final_status}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Investigation({ paymentId, onRecovered, onPick }) {
  const [rec, setRec] = useState(null);
  const [busy, setBusy] = useState(false);
  const [showWhy, setShowWhy] = useState(false);

  const load = () => {
    if (!paymentId) return;
    api.payment(paymentId).then(setRec).catch(() => setRec(null));
  };
  useEffect(load, [paymentId]);

  if (!paymentId) return <PaymentPicker onPick={onPick} />;
  if (!rec) return <div className="loading">Investigating {paymentId}…</div>;

  const { payment: p, diagnosis: d, decision: dec, policy: pol, outcome } = rec;

  const recover = async (forceFailure) => {
    setBusy(true);
    try {
      const updated = await api.recoverOne(paymentId, forceFailure);
      setRec(updated);
      onRecovered && onRecovered();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid cols-2">
      <div className="grid" style={{ gap: 16 }}>
        <div className="card">
          <div className="row">
            <h3 style={{ margin: 0 }}>Payment {p.payment_id}</h3>
            <div className="spacer" />
            <span className={`pill ${rec.final_status}`}>{rec.final_status}</span>
          </div>
          <table style={{ marginTop: 12 }}>
            <tbody>
              <tr><td className="muted">Amount</td><td className="right mono">{rupees(p.amount)}</td></tr>
              <tr><td className="muted">Method</td><td className="right">{p.payment_method}</td></tr>
              <tr><td className="muted">Failure code</td><td className="right mono">{p.failure_code}</td></tr>
              <tr><td className="muted">Customer history</td><td className="right">{p.previous_successes} ✓ / {p.previous_failures} ✗</td></tr>
              <tr><td className="muted">Preferred method</td><td className="right">{p.preferred_method}</td></tr>
              <tr><td className="muted">Retry count</td><td className="right mono">{p.retry_count}</td></tr>
              <tr><td className="muted">Risk score</td><td className="right mono">{p.risk_score?.toFixed(2)}</td></tr>
            </tbody>
          </table>
        </div>

        {d && (
          <div className="card">
            <h3>AI Diagnosis</h3>
            <div className="row">
              <span className={`pill ${d.category}`}>{d.category.replace(/_/g, " ")}</span>
              <div className="spacer" />
              <span className="muted">confidence {pct(d.confidence)} · {d.source}</span>
            </div>
            <p style={{ fontSize: 15 }}>{d.human_reason}</p>
            <div>
              {d.evidence.map((e, i) => (
                <div key={i} className={`evidence-item ${e.supports_recovery ? "yes" : "no"}`}>
                  <span className="mark">{e.supports_recovery ? "✓" : "✕"}</span>
                  <span>{e.text}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="grid" style={{ gap: 16 }}>
        {dec && (
          <div className="card">
            <h3>Recovery Decision</h3>
            <div className="row" style={{ alignItems: "baseline" }}>
              <div className="big-num">{pct(dec.recovery_probability)}</div>
              <span className="muted">recovery probability</span>
            </div>
            <table style={{ marginTop: 8 }}>
              <tbody>
                <tr><td className="muted">Recommended action</td><td className="right mono">{dec.action}</td></tr>
                <tr><td className="muted">Expected recovery</td><td className="right mono">{rupees(dec.expected_recovery_value)}</td></tr>
                <tr><td className="muted">Priority score</td><td className="right mono">{rupees(dec.recovery_priority)}</td></tr>
              </tbody>
            </table>
            <button className="btn secondary section-gap" onClick={() => setShowWhy((s) => !s)}>
              {showWhy ? "Hide" : "Why this action?"}
            </button>
            {showWhy && (
              <div className="section-gap">
                <div className="muted" style={{ fontSize: 13, marginBottom: 6 }}>Reasoning</div>
                {dec.rationale.map((r, i) => (
                  <div key={i} className="evidence-item yes">
                    <span className="mark">{i + 1}.</span><span>{r}</span>
                  </div>
                ))}
                <div className="muted section-gap" style={{ fontSize: 13, marginBottom: 6 }}>
                  Policy checks (deterministic)
                </div>
                <div className="checks">
                  {pol?.checks.map((c) => (
                    <div key={c.name} className={`check ${c.passed ? "pass" : "fail"}`}>
                      <span className="mark">{c.passed ? "✓" : "✕"}</span>
                      <span>{c.name.replace(/_/g, " ")}</span>
                      <span className="muted">— {c.detail}</span>
                    </div>
                  ))}
                </div>
                {pol?.requires_human_approval && (
                  <div className="banner warn section-gap">
                    High-value transaction — requires human approval before auto-recovery.
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <div className="card">
          <h3>Execute</h3>
          {outcome && (
            <div>
              <div className={`banner ${outcome.success ? "" : "warn"}`}
                style={outcome.success ? { background: "rgba(34,197,94,.12)", border: "1px solid var(--green)", color: "var(--green)" } : {}}>
                {outcome.message}
              </div>
              <div className="audit-log">
                {outcome.audit.map((a, i) => (
                  <div key={i} className="audit-line">
                    <span className="stage">{a.stage}</span>
                    <span>{a.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="row section-gap">
            <button
              className="btn"
              onClick={() => recover(false)}
              disabled={busy || outcome?.success || outcome?.failure_reason === "awaiting_customer_payment"}
              title={outcome?.success ? "Already recovered and verified" : outcome?.failure_reason === "awaiting_customer_payment" ? "Waiting for Razorpay payment confirmation" : "Execute or retry the recovery action"}
            >
              {busy ? "Executing…" : outcome?.success ? "✓ Recovered" : outcome ? "↻ Retry recovery" : "▶ Recover this payment"}
            </button>
            {!outcome?.success && outcome?.failure_reason !== "awaiting_customer_payment" && (
              <button className="btn danger" onClick={() => recover(true)} disabled={busy}
                title="Simulate the recovery API being unavailable">
                Simulate API failure
              </button>
            )}
            {outcome?.failure_reason === "awaiting_customer_payment" && (
              <button className="btn secondary" onClick={load} disabled={busy}>
                ↻ Refresh payment status
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
