// Thin API client. In dev, Vite proxies /api to the FastAPI backend.
const BASE = "/api";

async function req(path, opts = {}) {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  health: () => req("/health"),
  metrics: () => req("/metrics"),
  pipeline: () => req("/pipeline"),
  categories: () => req("/categories"),
  queue: (limit = 25) => req(`/queue?limit=${limit}`),
  payments: (status) => req(`/payments${status ? `?status=${status}` : ""}`),
  payment: (id) => req(`/payments/${id}`),
  recoverOne: (id, forceFailure = false) =>
    req(`/payments/${id}/recover`, {
      method: "POST",
      body: JSON.stringify({ force_failure: forceFailure }),
    }),
  recoverBatch: () => req("/recover-batch", { method: "POST" }),
  audit: (limit = 200) => req(`/audit?limit=${limit}`),
  chat: (message) =>
    req("/chat", { method: "POST", body: JSON.stringify({ message }) }),
  reset: () => req("/reset", { method: "POST" }),
};

export const rupees = (x) =>
  x == null ? "—" : `₹${Number(x).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

export const pct = (x) => (x == null ? "—" : `${(x * 100).toFixed(0)}%`);
