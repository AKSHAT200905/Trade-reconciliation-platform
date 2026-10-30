import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { formatDate, formatDateTime, formatMoney, formatPercent, humanize } from "../format.js";

export default function Dashboard({ notify, onOpenRun, onGoToTrades }) {
  const [summary, setSummary] = useState(null);
  const [dates, setDates] = useState([]);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const [s, d, r] = await Promise.all([api.summary(), api.tradeDates(), api.listRuns()]);
      setSummary(s);
      setDates(d);
      setRuns(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function loadSample() {
    setBusy("sample");
    try {
      const results = await api.loadSample();
      const total = results.reduce((n, r) => n + r.inserted + r.updated, 0);
      notify(`Loaded ${total} sample trades from both sources`);
      await load();
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy("");
    }
  }

  async function reconcile(tradeDate) {
    setBusy(tradeDate);
    try {
      const run = await api.runRecon(tradeDate);
      notify(`Run #${run.id}: ${run.matched_count} matched, ${run.break_count} breaks (${formatPercent(run.match_rate)} match rate)`);
      await load();
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy("");
    }
  }

  if (loading) return <div className="panel muted">Loading dashboard...</div>;
  if (error)
    return (
      <div className="panel error-panel">
        <strong>Could not load the dashboard.</strong> {error}
        <div>
          <button type="button" className="btn" onClick={load}>
            Retry
          </button>
        </div>
      </div>
    );

  const latest = summary?.latest_run;
  const maxCount = Math.max(1, ...(summary?.open_breaks_by_type || []).map((t) => t.count));

  return (
    <div className="stack">
      <section className="kpis">
        <Kpi label="Open breaks" value={summary.open_breaks} tone={summary.open_breaks ? "warn" : "ok"} />
        <Kpi label="Open exposure" value={formatMoney(summary.open_exposure, true)} hint={formatMoney(summary.open_exposure)} />
        <Kpi
          label="Latest match rate"
          value={latest ? formatPercent(latest.match_rate) : "-"}
          hint={latest ? `Run #${latest.id} for ${formatDate(latest.trade_date)}` : "No runs yet"}
        />
        <Kpi label="Resolved breaks" value={summary.resolved_breaks} hint={`${summary.total_runs} runs across ${summary.dates_reconciled} dates`} />
      </section>

      <div className="grid-2">
        <section className="panel">
          <div className="panel-head">
            <h2>Trade dates</h2>
            <button type="button" className="btn ghost" onClick={loadSample} disabled={busy === "sample"}>
              {busy === "sample" ? "Loading..." : "Load sample data"}
            </button>
          </div>
          {dates.length === 0 ? (
            <Empty>
              No trades yet. Load the sample data or{" "}
              <button type="button" className="link" onClick={onGoToTrades}>
                upload CSV files
              </button>
              .
            </Empty>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Trade date</th>
                  <th className="num">Internal</th>
                  <th className="num">Custodian</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {dates.map((d) => (
                  <tr key={d.trade_date}>
                    <td>{formatDate(d.trade_date)}</td>
                    <td className="num">{d.internal_count}</td>
                    <td className="num">{d.custodian_count}</td>
                    <td className="right">
                      <button type="button" className="btn small" onClick={() => reconcile(d.trade_date)} disabled={Boolean(busy)}>
                        {busy === d.trade_date ? "Running..." : "Reconcile"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>Open breaks by type</h2>
            <span className="muted small">Latest run per date</span>
          </div>
          {summary.open_breaks_by_type.length === 0 ? (
            <Empty>{summary.total_runs ? "No open breaks. Everything is reconciled." : "Run a reconciliation to see breaks."}</Empty>
          ) : (
            <ul className="bars">
              {summary.open_breaks_by_type.map((t) => (
                <li key={t.break_type}>
                  <div className="bar-label">
                    <span>{humanize(t.break_type)}</span>
                    <span className="muted">
                      {t.count} &middot; {formatMoney(t.exposure, true)}
                    </span>
                  </div>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${(t.count / maxCount) * 100}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="panel">
        <div className="panel-head">
          <h2>Reconciliation runs</h2>
        </div>
        {runs.length === 0 ? (
          <Empty>No runs yet. Pick a trade date above and click Reconcile.</Empty>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Trade date</th>
                  <th className="num">Internal</th>
                  <th className="num">Custodian</th>
                  <th className="num">Matched</th>
                  <th className="num">Breaks</th>
                  <th className="num">Match rate</th>
                  <th className="num">Exposure</th>
                  <th>Completed</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id}>
                    <td>#{r.id}</td>
                    <td>{formatDate(r.trade_date)}</td>
                    <td className="num">{r.internal_count}</td>
                    <td className="num">{r.custodian_count}</td>
                    <td className="num">{r.matched_count}</td>
                    <td className="num">{r.break_count}</td>
                    <td className="num">{formatPercent(r.match_rate)}</td>
                    <td className="num">{formatMoney(r.total_exposure, true)}</td>
                    <td>{formatDateTime(r.completed_at)}</td>
                    <td className="right">
                      <button type="button" className="btn small ghost" onClick={() => onOpenRun(r.id)}>
                        View breaks
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function Kpi({ label, value, hint, tone }) {
  return (
    <div className={`kpi ${tone || ""}`}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {hint && <div className="kpi-hint">{hint}</div>}
    </div>
  );
}

function Empty({ children }) {
  return <div className="empty">{children}</div>;
}
