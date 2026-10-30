import { useCallback, useRef, useState } from "react";
import Dashboard from "./components/Dashboard.jsx";
import Trades from "./components/Trades.jsx";
import Breaks from "./components/Breaks.jsx";

const TABS = [
  { id: "dashboard", label: "Dashboard" },
  { id: "trades", label: "Trades" },
  { id: "breaks", label: "Breaks" },
];

export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [toast, setToast] = useState(null);

  const timer = useRef(null);

  const notify = useCallback((message, kind = "success") => {
    setToast({ message, kind, id: Date.now() });
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setToast(null), 4500);
  }, []);

  const openRun = useCallback((runId) => {
    setSelectedRunId(runId);
    setTab("breaks");
  }, []);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <svg viewBox="0 0 32 32" className="brand-mark" aria-hidden="true">
            <rect width="32" height="32" rx="7" />
            <path d="M8 11h11l-3-3M24 21H13l3 3" />
          </svg>
          <div>
            <div className="brand-name">TradeRecon</div>
            <div className="brand-sub">Trade reconciliation platform</div>
          </div>
        </div>
        <nav className="tabs" aria-label="Main">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={tab === t.id ? "tab active" : "tab"}
              aria-current={tab === t.id ? "page" : undefined}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="content">
        {tab === "dashboard" && <Dashboard notify={notify} onOpenRun={openRun} onGoToTrades={() => setTab("trades")} />}
        {tab === "trades" && <Trades notify={notify} onOpenRun={openRun} />}
        {tab === "breaks" && <Breaks notify={notify} runId={selectedRunId} onSelectRun={setSelectedRunId} />}
      </main>

      {toast && (
        <div key={toast.id} className={`toast ${toast.kind}`} role="status">
          {toast.message}
        </div>
      )}
    </div>
  );
}
