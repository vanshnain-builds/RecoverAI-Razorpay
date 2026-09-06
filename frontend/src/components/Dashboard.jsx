import React, { useEffect, useState } from "react";
import { api, rupees, pct } from "../api.js";

function Metric({ value, label, tone }) {
  return (
    <div className={`card metric ${tone || ""}`}>
      <div className="value">{value}</div>
      <div className="label">{label}</div>
    </div>
  );
}

const PIPE_STAGES = [
  { key: "failed", label: "Failed", color: "var(--red)" },
  { key: "diagnosed", label: "Diagnosed", color: "var(--purple)" },
  { key: "recoverable", label: "Recoverable", color: "var(--accent)" },
  { key: "actions_executed", label: "Actions executed", color: "var(--amber)" },
  { key: "recovered", label: "Recovered", color: "var(--green)" },
];

export default function Dashboard({ version, onRefresh, onOpenPayment }) {
  const [m, setM] = useState(null);
  const [pipe, setPipe] = useState(null);
  const [cats, setCats] = useState(null);
  const [busy, setBusy] = useState(false);
  const [batchResult, setBatchResult] = useState(null);
  const [batchError, setBatchError] = useState("");

  const load = () => {
    api.metrics().then(setM).catch(() => setM({}));
    api.pipeline().then(setPipe).catch(() => setPipe({}));
    api.categories().then(setCats).catch(() => setCats({}));
  };

  useEffect(load, [version]);

  const runBatch = async () => {
    setBusy(true);
    setBatchError("");
    try {
      const result = await api.recoverBatch();
      setBatchResult(result);
      load();
      onRefresh && onRefresh();
    } catch (err) {
      setBatchError(err.message || "Recovery batch failed");
    } finally {
      setBusy(false);
    }
  };

  if (!m || !pipe) return <div className="loading">Loading merchant data…</div>;

  // Backend returns `executed`; keep the UI's existing `actions_executed` label.
  const pipeline = { ...pipe, actions_executed: pipe.actions_executed ?? pipe.executed ?? 0 };
  const maxPipe = Math.max(...PIPE_STAGES.map((s) => Number(pipeline[s.key] ?? 0)), 1);

  const categoryRows = Object.entries(cats || {}).map(([key, value]) => {
    // Current backend returns objects: { count, amount, recoverable_count, recoverable_amount }.
    // Older/demo responses may return a plain number, so support both shapes.
    if (typeof value === "number") {
      return { key, count: value, amount: 0, recoverable_count: 0, recoverable_amount: 0 };
    }
    return {
      key,
      count: Number(value?.count ?? 0),
      amount: Number(value?.amount ?? 0),
      recoverable_count: Number(value?.recoverable_count ?? 0),
      recoverable_amount: Number(value?.recoverable_amount ?? 0),
    };
  }).sort((a, b) => b.count - a.count);

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="grid metrics four">
        <Metric tone="red" value={rupees(m.at_risk_amount ?? m.revenue_at_risk)} label="At risk · original failed revenue" />
        <Metric tone="amber" value={rupees(m.recoverable_total)} label="Recoverable · identified opportunity" />
        <Metric tone="green" value={rupees(m.recovered_amount)} label="Recovered · verified outcome" />
        <Metric tone="amber" value={rupees(m.remaining_recoverable_amount ?? m.recoverable_amount)} label="Remaining recoverable" />
      </div>
      <div className="metric-definitions">
        <span><b>At risk</b> = original failed-payment amount.</span>
        <span><b>Recoverable</b> = AI opportunity above the recovery threshold.</span>
        <span><b>Recovered</b> = successful/verified recovery outcomes.</span>
        <span><b>Remaining</b> = recoverable opportunity not yet recovered.</span>
      </div>
      <div className="grid metrics">
        <Metric value={m.failed_count ?? 0} label="Failed payments remaining" />
        <Metric value={pct(m.recovery_rate)} label="Recovery rate" />
        <Metric value={m.actions_executed ?? 0} label="Recovery actions taken" />
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h3>AI Recovery Pipeline</h3>
          <div className="pipeline">
            {PIPE_STAGES.map((s) => {
              const val = Number(pipeline[s.key] ?? 0);
              const w = 30 + (val / maxPipe) * 70;
              return (
                <div className="pipe-row" key={s.key}>
                  <div className="pipe-label">{s.label}</div>
                  <div
                    className="pipe-bar"
                    style={{ width: `${w}%`, background: s.color + "22", border: `1px solid ${s.color}55` }}
                  >
                    <span className="pipe-count">{val}</span>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="section-gap">
            <div className="row">
              <button className="btn" onClick={runBatch} disabled={busy}>
                {busy ? "Recovering…" : "▶ Recover eligible payments"}
              </button>
              <span className="muted">
                Runs the full agentic loop across the batch, safely.
              </span>
            </div>
            {batchResult && (
              <div className="banner" style={{ marginTop: 12 }}>
                Batch complete: {batchResult.actions_executed} actions executed · {batchResult.successful_recoveries} recovered · {rupees(batchResult.recovered_amount)} recovered.
              </div>
            )}
            {batchError && (
              <div className="banner warn" style={{ marginTop: 12 }}>
                {batchError}
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <h3>Failure Categories</h3>
          {categoryRows.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Category</th>
                  <th className="right">Payments</th>
                  <th className="right">Amount</th>
                </tr>
              </thead>
              <tbody>
                {categoryRows.map((row) => (
                  <tr key={row.key}>
                    <td>
                      <span className={`pill ${row.key}`}>{row.key.replace(/_/g, " ")}</span>
                    </td>
                    <td className="right mono">{row.count}</td>
                    <td className="right mono">{rupees(row.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="muted">No failure categories available.</div>
          )}
          <div className="section-gap muted" style={{ fontSize: 13 }}>
            Escalated: {rupees(m.escalated_amount ?? 0)} · Abandoned by policy:{" "}
            {rupees(m.abandoned_amount ?? 0)}
          </div>
        </div>
      </div>
    </div>
  );
}
