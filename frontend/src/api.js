const TRADE_API = (import.meta.env.VITE_TRADE_API_URL || "").replace(/\/$/, "");
const RECON_API = (import.meta.env.VITE_RECON_API_URL || "").replace(/\/$/, "");

async function request(url, options = {}) {
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new Error("Cannot reach the server. Check that the services are running.");
  }
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof body === "object" && body ? body.detail : body;
    if (Array.isArray(detail)) {
      throw new Error(detail.map((d) => String(d.msg || d).replace(/^Value error, /, "")).join("; "));
    }
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return body;
}

function query(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") search.set(key, value);
  });
  const text = search.toString();
  return text ? `?${text}` : "";
}

export const api = {
  uploadTrades(source, file) {
    const form = new FormData();
    form.append("source", source);
    form.append("file", file);
    return request(`${TRADE_API}/api/trades/upload`, { method: "POST", body: form });
  },
  loadSample() {
    return request(`${TRADE_API}/api/trades/sample`, { method: "POST" });
  },
  listTrades(params) {
    return request(`${TRADE_API}/api/trades${query(params)}`);
  },
  tradeDates() {
    return request(`${TRADE_API}/api/trades/dates`);
  },
  clearTrades() {
    return request(`${TRADE_API}/api/trades`, { method: "DELETE" });
  },
  runRecon(tradeDate) {
    return request(`${RECON_API}/api/recon/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trade_date: tradeDate }),
    });
  },
  listRuns() {
    return request(`${RECON_API}/api/recon/runs`);
  },
  listBreaks(runId, params) {
    return request(`${RECON_API}/api/recon/runs/${runId}/breaks${query(params)}`);
  },
  updateBreak(breakId, payload) {
    return request(`${RECON_API}/api/recon/breaks/${breakId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },
  summary() {
    return request(`${RECON_API}/api/recon/summary`);
  },
  exportUrl(runId) {
    return `${RECON_API}/api/recon/runs/${runId}/breaks.csv`;
  },
};
