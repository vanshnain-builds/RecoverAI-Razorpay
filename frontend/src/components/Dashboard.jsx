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
    api.metrics().then(setM).catch(() => {});
    api.pipeline().then(setPipe).catch(() => {});
    api.categories().then(setCats).catch(() => {});
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

  const maxPipe = Math.max(...PIPE_STAGES.map((s) => pipe[s.key] || 0), 1);

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
        <Metric value={m.failed_count} label="Failed payments remaining" />
        <Metric value={pct(m.recovery_rate)} label="Recovery rate" />
        <Metric value={m.actions_executed} label="Recovery actions taken" />
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h3>AI Recovery Pipeline</h3>
          <div className="pipeline">
            {PIPE_STAGES.map((s) => {
              const val = pipe[s.key] || 0;
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
          {cats ? (
            <table>
              <tbody>
                {Object.entries(cats)
                  .sort((a, b) => b[1] - a[1])
                  .map(([k, v]) => (
                    <tr key={k}>
                      <td>
                        <span className={`pill ${k}`}>{k.replace(/_/g, " ")}</span>
                      </td>
                      <td className="right mono">{v}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          ) : (
            <div className="muted">—</div>
          )}
          <div className="section-gap muted" style={{ fontSize: 13 }}>
            Escalated: {rupees(m.escalated_amount)} · Abandoned by policy:{" "}
            {rupees(m.abandoned_amount)}
          </div>
        </div>
      </div>
    </div>
  );
}
