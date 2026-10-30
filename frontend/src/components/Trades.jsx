import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { formatDate, formatMoney, formatNumber } from "../format.js";

const PAGE_SIZE = 25;

export default function Trades({ notify, onOpenRun }) {
  const [filters, setFilters] = useState({ source: "", trade_date: "", search: "" });
  const [page, setPage] = useState(0);
  const [data, setData] = useState({ total: 0, items: [] });
  const [dates, setDates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [trades, tradeDates] = await Promise.all([
        api.listTrades({ ...filters, limit: PAGE_SIZE, offset: page * PAGE_SIZE }),
        api.tradeDates(),
      ]);
      setData(trades);
      setDates(tradeDates);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => {
    load();
  }, [load]);

  function updateFilter(name, value) {
    setPage(0);
    setFilters((f) => ({ ...f, [name]: value }));
  }

  async function clearAll() {
    if (!window.confirm("Delete all trades from both sources?")) return;
    try {
      const result = await api.clearTrades();
      notify(`Deleted ${result.deleted} trades`);
      setPage(0);
      await load();
    } catch (e) {
      notify(e.message, "error");
    }
  }

  const pages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));

  return (
    <div className="stack">
      <div className="grid-2">
        <UploadCard source="INTERNAL" title="Internal trading desk" notify={notify} onDone={load} />
        <UploadCard source="CUSTODIAN" title="Custodian bank" notify={notify} onDone={load} />
      </div>

      <section className="panel">
        <div className="panel-head">
          <h2>Trades</h2>
          <button type="button" className="btn ghost danger" onClick={clearAll} disabled={data.total === 0}>
            Delete all
          </button>
        </div>

        <div className="filters">
          <label>
            Source
            <select value={filters.source} onChange={(e) => updateFilter("source", e.target.value)}>
              <option value="">All</option>
              <option value="INTERNAL">Internal</option>
              <option value="CUSTODIAN">Custodian</option>
            </select>
          </label>
          <label>
            Trade date
            <select value={filters.trade_date} onChange={(e) => updateFilter("trade_date", e.target.value)}>
              <option value="">All dates</option>
              {dates.map((d) => (
                <option key={d.trade_date} value={d.trade_date}>
                  {formatDate(d.trade_date)}
                </option>
              ))}
            </select>
          </label>
          <label className="grow">
            Search
            <input
              type="search"
              placeholder="Trade ref, ISIN or counterparty"
              value={filters.search}
              maxLength={64}
              onChange={(e) => updateFilter("search", e.target.value)}
            />
          </label>
        </div>

        {error ? (
          <div className="error-panel">{error}</div>
        ) : (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Trade ref</th>
                    <th>Source</th>
                    <th>Trade date</th>
                    <th>Settles</th>
                    <th>ISIN</th>
                    <th>Side</th>
                    <th className="num">Quantity</th>
                    <th className="num">Price</th>
                    <th className="num">Notional</th>
                    <th>Counterparty</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((t) => (
                    <tr key={t.id}>
                      <td className="mono">{t.trade_ref}</td>
                      <td>
                        <span className={`pill ${t.source === "INTERNAL" ? "blue" : "violet"}`}>{t.source === "INTERNAL" ? "Internal" : "Custodian"}</span>
                      </td>
                      <td>{formatDate(t.trade_date)}</td>
                      <td>{formatDate(t.settlement_date)}</td>
                      <td className="mono">{t.instrument}</td>
                      <td>
                        <span className={t.side === "BUY" ? "side buy" : "side sell"}>{t.side}</span>
                      </td>
                      <td className="num">{formatNumber(t.quantity)}</td>
                      <td className="num">{formatNumber(t.price)}</td>
                      <td className="num">{formatMoney(Number(t.quantity) * Number(t.price))}</td>
                      <td>{t.counterparty}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!loading && data.items.length === 0 && <div className="empty">No trades match these filters.</div>}
            <div className="pager">
              <span className="muted small">
                {data.total} trades{loading ? " · loading..." : ""}
              </span>
              <div>
                <button type="button" className="btn small ghost" onClick={() => setPage((p) => p - 1)} disabled={page === 0}>
                  Previous
                </button>
                <span className="small page-label">
                  Page {page + 1} of {pages}
                </span>
                <button type="button" className="btn small ghost" onClick={() => setPage((p) => p + 1)} disabled={page + 1 >= pages}>
                  Next
                </button>
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}

function UploadCard({ source, title, notify, onDone }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  async function submit(event) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setResult(null);
    try {
      const res = await api.uploadTrades(source, file);
      setResult(res);
      notify(`${title}: ${res.inserted} added, ${res.updated} updated, ${res.rejected.length} rejected`, res.rejected.length ? "warn" : "success");
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      await onDone();
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>{title}</h2>
        <span className={`pill ${source === "INTERNAL" ? "blue" : "violet"}`}>{source === "INTERNAL" ? "Internal" : "Custodian"}</span>
      </div>
      <form className="upload" onSubmit={submit}>
        <input ref={inputRef} type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] || null)} aria-label={`${title} CSV file`} />
        <button type="submit" className="btn" disabled={!file || busy}>
          {busy ? "Uploading..." : "Upload CSV"}
        </button>
      </form>
      <p className="muted small">
        Columns: trade_ref, trade_date, settlement_date, instrument, side, quantity, price, currency, counterparty
      </p>
      {result && result.rejected.length > 0 && (
        <div className="rejected">
          <strong>{result.rejected.length} rows rejected</strong>
          <ul>
            {result.rejected.slice(0, 8).map((r) => (
              <li key={`${r.row}-${r.trade_ref}`}>
                Row {r.row}
                {r.trade_ref ? ` (${r.trade_ref})` : ""}: {r.error}
              </li>
            ))}
          </ul>
          {result.rejected.length > 8 && <div className="muted small">and {result.rejected.length - 8} more</div>}
        </div>
      )}
    </section>
  );
}
