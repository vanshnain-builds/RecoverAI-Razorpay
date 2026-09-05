import React, { useEffect, useState } from "react";
import { api, rupees, pct } from "../api.js";

export default function Queue({ version, onOpenPayment }) {
  const [rows, setRows] = useState(null);

  useEffect(() => {
    api.queue(25).then(setRows).catch(() => setRows([]));
  }, [version]);

  if (!rows) return <div className="loading">Prioritising recovery queue…</div>;

  return (
    <div className="card">
      <h3>AI Recovery Queue — ordered by expected recovered value</h3>
      <p className="muted" style={{ marginTop: -6, fontSize: 13 }}>
        Priority = expected recovery value, discounted for risk and operational
        effort. The agent decides <em>what to recover first</em>, not just
        whether a payment is recoverable.
      </p>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Payment</th>
            <th className="right">Amount</th>
            <th>Category</th>
            <th>Recommended action</th>
            <th className="right">p(recover)</th>
            <th className="right">Expected ₹</th>
            <th className="right">Priority</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr
              key={r.payment_id}
              className="clickable"
              onClick={() => onOpenPayment(r.payment_id)}
            >
              <td className="muted">{i + 1}</td>
              <td className="mono">{r.payment_id}</td>
              <td className="right mono">{rupees(r.amount)}</td>
              <td>
                <span className={`pill ${r.category}`}>
                  {r.category?.replace(/_/g, " ")}
                </span>
              </td>
              <td className="mono">{r.action}</td>
              <td className="right">{pct(r.recovery_probability)}</td>
              <td className="right mono">{rupees(r.expected_recovery_value)}</td>
              <td className="right mono">{rupees(r.recovery_priority)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
