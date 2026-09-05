import React, { useEffect, useState, useCallback } from "react";
import { api } from "./api.js";
import Dashboard from "./components/Dashboard.jsx";
import Queue from "./components/Queue.jsx";
import Investigation from "./components/Investigation.jsx";
import AuditTrail from "./components/AuditTrail.jsx";
import Chat from "./components/Chat.jsx";

const TABS = [
  { id: "dashboard", label: "Command Center" },
  { id: "queue", label: "Recovery Queue" },
  { id: "investigate", label: "Investigation" },
  { id: "audit", label: "Audit Trail" },
  { id: "chat", label: "Ask RecoverAI" },
];

export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [selectedPayment, setSelectedPayment] = useState(null);
  const [version, setVersion] = useState(0); // bump to force refresh across tabs
  const [online, setOnline] = useState(null);
  const [health, setHealth] = useState(null);

  const refresh = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    api
      .health()
      .then((h) => {
        setHealth(h);
        setOnline(true);
      })
      .catch(() => setOnline(false));
  }, [version]);

  const openInvestigation = (paymentId) => {
    setSelectedPayment(paymentId);
    setTab("investigate");
  };

  return (
    <div className="app">
      <div className="header">
        <div className="brand">
          <h1>
            <span className="logo">◆</span> RecoverAI
          </h1>
          <span className="tag">Autonomous Revenue Recovery</span>
        </div>
        <div className="row">
          {health && (
            <>
              <span
                className={`pill ${health.data_source === "razorpay" ? "recovered" : "customer_action"}`}
                title={
                  health.data_source === "razorpay"
                    ? `Ingesting real Razorpay payments (${health.razorpay_mode || "test"} mode) · ${health.payments_loaded} loaded`
                    : "Using the built-in synthetic dataset (no Razorpay keys configured)"
                }
              >
                {health.data_source === "razorpay"
                  ? `● Live Razorpay (${health.razorpay_mode || "test"})`
                  : "● Synthetic data"}
              </span>
              <span
                className={`pill ${health.persistence === "supabase" ? "payment_method_issue" : "unknown"}`}
                title={
                  health.persistence === "supabase"
                    ? "Persisting to Supabase" +
                      (health.persistence_error ? ` · last error: ${health.persistence_error}` : "")
                    : "In-memory only (no Supabase keys configured)"
                }
              >
                {health.persistence === "supabase" ? "◆ Supabase" : "◆ In-memory"}
              </span>
            </>
          )}
          {online === false && (
            <span className="pill high_risk">backend offline</span>
          )}
          <button
            className="btn secondary"
            onClick={async () => {
              await api.reset();
              refresh();
            }}
          >
            Reset demo
          </button>
        </div>
      </div>
      <div className="subhead">
        Detect revenue slipping away → understand why → choose the best recovery
        action → execute it safely → measure the money recovered.
      </div>

      {online === false && (
        <div className="banner warn">
          Cannot reach the backend at <span className="mono">/api</span>. Start it
          with <span className="mono">uvicorn app.main:app --reload</span> in the
          backend folder, then reload.
        </div>
      )}

      <div className="tabs">
        {TABS.map((t) => (
          <div
            key={t.id}
            className={`tab ${tab === t.id ? "active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </div>
        ))}
      </div>

      {tab === "dashboard" && (
        <Dashboard
          version={version}
          onRefresh={refresh}
          onOpenPayment={openInvestigation}
        />
      )}
      {tab === "queue" && (
        <Queue version={version} onOpenPayment={openInvestigation} />
      )}
      {tab === "investigate" && (
        <Investigation
          paymentId={selectedPayment}
          onRecovered={refresh}
          onPick={setSelectedPayment}
        />
      )}
      {tab === "audit" && <AuditTrail version={version} />}
      {tab === "chat" && <Chat onRefresh={refresh} />}
    </div>
  );
}
