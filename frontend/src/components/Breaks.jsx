import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { formatDate, formatDateTime, formatMoney, formatPercent, humanize } from "../format.js";

const BREAK_TYPES = [
  "MISSING_IN_CUSTODIAN",
  "MISSING_IN_INTERNAL",
  "INSTRUMENT_MISMATCH",
  "SIDE_MISMATCH",
  "QUANTITY_MISMATCH",
  "PRICE_MISMATCH",
  "CURRENCY_MISMATCH",
  "SETTLEMENT_DATE_MISMATCH",
  "COUNTERPARTY_MISMATCH",
];

export default function Breaks({ notify, runId, onSelectRun }) {
  const [runs, setRuns] = useState([]);
  const [breaks, setBreaks] = useState([]);
  const [filters, setFilters] = useState({ status: "OPEN", break_type: "" });
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [loadingBreaks, setLoadingBreaks] = useState(false);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(null);

  useEffect(() => {
    let active = true;
    api
      .listRuns()
      .then((list) => {
        if (!active) return;
        setRuns(list);
        if (list.length && !list.some((r) => r.id === runId)) onSelectRun(list[0].id);
      })
      .catch((e) => active && setError(e.message))
      .finally(() => active && setLoadingRuns(false));
    return () => {
      active = false;
    };
  }, [runId, onSelectRun]);

  const loadBreaks = useCallback(async () => {
    if (!runId) return;
    setLoadingBreaks(true);
    setError("");
    try {
      setBreaks(await api.listBreaks(runId, filters));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingBreaks(false);
    }
  }, [runId, filters]);

  useEffect(() => {
    loadBreaks();
  }, [loadBreaks]);

  async function save(item, payload) {
    try {
      const updated = await api.updateBreak(item.id, payload);
      notify(updated.status === "RESOLVED" ? `Resolved ${item.trade_ref}` : `Reopened ${item.trade_ref}`);
      setEditing(null);
      await loadBreaks();
      return true;
    } catch (e) {
      notify(e.message, "error");
      return false;
    }
  }

  if (loadingRuns) return <div className="panel muted">Loading runs...</div>;
  if (!runs.length)
    return (
      <div className="panel">
        <div className="empty">{error || "No reconciliation runs yet. Go to the Dashboard and reconcile a trade date."}</div>
      </div>
    );

  const run = runs.find((r) => r.id === runId) || runs[0];
  const shownExposure = breaks.reduce((sum, b) => sum + Number(b.exposure), 0);

  return (
    <div className="stack">
      <section className="panel">
        <div className="panel-head">
          <h2>Run #{run.id}</h2>
          <div className="row">
            <select value={run.id} onChange={(e) => onSelectRun(Number(e.target.value))} aria-label="Select run">
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  Run #{r.id} · {formatDate(r.trade_date)}
                </option>
              ))}
            </select>
            <a className="btn ghost" href={api.exportUrl(run.id)} download>
              Export CSV
            </a>
          </div>
        </div>
        <div className="run-stats">
          <Stat label="Trade date" value={formatDate(run.trade_date)} />
          <Stat label="Internal / Custodian" value={`${run.internal_count} / ${run.custodian_count}`} />
          <Stat label="Matched" value={run.matched_count} />
          <Stat label="Breaks" value={run.break_count} />
          <Stat label="Match rate" value={formatPercent(run.match_rate)} />
          <Stat label="Exposure" value={formatMoney(run.total_exposure)} />
          <Stat label="Price tolerance" value={`${Number(run.price_tolerance_bps)} bp`} />
          <Stat label="Completed" value={formatDateTime(run.completed_at)} />
        </div>
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Breaks</h2>
          <span className="muted small">
            {breaks.length} shown · {formatMoney(shownExposure)} exposure
          </span>
        </div>
        <div className="filters">
          <label>
            Status
            <select value={filters.status} onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}>
              <option value="">All</option>
              <option value="OPEN">Open</option>
              <option value="RESOLVED">Resolved</option>
            </select>
          </label>
          <label>
            Break type
            <select value={filters.break_type} onChange={(e) => setFilters((f) => ({ ...f, break_type: e.target.value }))}>
              <option value="">All types</option>
              {BREAK_TYPES.map((t) => (
                <option key={t} value={t}>
                  {humanize(t)}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error ? (
          <div className="error-panel">{error}</div>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Trade ref</th>
                  <th>Break type</th>
                  <th>Internal</th>
                  <th>Custodian</th>
                  <th className="num">Exposure</th>
                  <th>Counterparty</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {breaks.map((b) => (
                  <BreakRow
                    key={b.id}
                    item={b}
                    editing={editing === b.id}
                    onEdit={() => setEditing(b.id)}
                    onCancel={() => setEditing(null)}
                    onSave={save}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!loadingBreaks && !error && breaks.length === 0 && <div className="empty">No breaks match these filters.</div>}
        {loadingBreaks && <div className="muted small pad">Loading breaks...</div>}
      </section>
    </div>
  );
}

function BreakRow({ item, editing, onEdit, onCancel, onSave }) {
  const [comment, setComment] = useState("");
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);

  async function resolve(event) {
    event.preventDefault();
    setSaving(true);
    const ok = await onSave(item, { status: "RESOLVED", comment, resolved_by: name });
    setSaving(false);
    if (ok) {
      setComment("");
      setName("");
    }
  }

  return (
    <>
      <tr>
        <td className="mono">{item.trade_ref}</td>
        <td>
          <span className={`pill type-${item.break_type.toLowerCase()}`}>{humanize(item.break_type)}</span>
        </td>
        <td className="mono small">{item.internal_value ?? <span className="muted">missing</span>}</td>
        <td className="mono small">{item.custodian_value ?? <span className="muted">missing</span>}</td>
        <td className="num">{formatMoney(item.exposure)}</td>
        <td>{item.counterparty}</td>
        <td>
          {item.status === "OPEN" ? (
            <span className="pill warn">Open</span>
          ) : (
            <span className="pill ok" title={item.resolution_comment || ""}>
              Resolved
            </span>
          )}
        </td>
        <td className="right">
          {item.status === "OPEN" ? (
            !editing && (
              <button type="button" className="btn small" onClick={onEdit}>
                Resolve
              </button>
            )
          ) : (
            <button type="button" className="btn small ghost" onClick={() => onSave(item, { status: "OPEN" })}>
              Reopen
            </button>
          )}
        </td>
      </tr>
      {item.status === "RESOLVED" && item.resolution_comment && (
        <tr className="note-row">
          <td colSpan={8}>
            <span className="muted small">
              {item.resolved_by} · {formatDateTime(item.resolved_at)}: {item.resolution_comment}
            </span>
          </td>
        </tr>
      )}
      {editing && (
        <tr className="edit-row">
          <td colSpan={8}>
            <form className="resolve-form" onSubmit={resolve}>
              <input
                type="text"
                placeholder="Resolution comment (required)"
                value={comment}
                maxLength={1000}
                onChange={(e) => setComment(e.target.value)}
                required
                autoFocus
              />
              <input type="text" placeholder="Your name" value={name} maxLength={64} onChange={(e) => setName(e.target.value)} />
              <button type="submit" className="btn small" disabled={saving || !comment.trim()}>
                {saving ? "Saving..." : "Confirm"}
              </button>
              <button type="button" className="btn small ghost" onClick={onCancel}>
                Cancel
              </button>
            </form>
          </td>
        </tr>
      )}
    </>
  );
}

function Stat({ label, value }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}
