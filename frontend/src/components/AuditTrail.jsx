import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function AuditTrail({ version }) {
  const [entries, setEntries] = useState(null);

  useEffect(() => {
    api.audit(300).then(setEntries).catch(() => setEntries([]));
  }, [version]);

  if (!entries) return <div className="loading">Loading audit trail…</div>;

  return (
    <div className="card">
      <h3>Audit Trail — every action the agent took</h3>
      {entries.length === 0 ? (
        <div className="muted">
          No actions yet. Run a recovery from the Command Center or Investigation
          tab to populate the trail.
        </div>
      ) : (
        <div className="audit-log" style={{ maxHeight: 560 }}>
          {entries
            .slice()
            .reverse()
            .map((a, i) => (
              <div key={i} className="audit-line">
                <span className="ts">{a.ts?.replace("T", " ")}</span>
                <span className="stage">{a.stage}</span>
                <span className="mono muted">{a.payment_id}</span>
                <span>{a.message}</span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
