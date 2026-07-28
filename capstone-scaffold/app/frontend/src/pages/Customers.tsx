import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCustomers, type CustomerFilters } from "@/hooks/customers";
import { currency, pct, segmentName, churnTone } from "@/lib/format";

const SEGMENTS = ["", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"];
const PAGE_SIZE = 25;

function useDebounced<T>(value: T, ms = 250): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export default function Customers() {
  const navigate = useNavigate();
  const [segment, setSegment] = useState("");
  const [minLtv, setMinLtv] = useState("");
  const [maxChurn, setMaxChurn] = useState("");
  const [page, setPage] = useState(1);

  const filters: CustomerFilters = useMemo(
    () => ({
      segment: segment || undefined,
      min_ltv: minLtv ? Number(minLtv) : undefined,
      max_churn: maxChurn ? Number(maxChurn) : undefined,
    }),
    [segment, minLtv, maxChurn]
  );
  const debounced = useDebounced(filters);
  useEffect(() => setPage(1), [debounced]);

  const { data, isLoading, isError, error } = useCustomers(debounced, page, PAGE_SIZE);
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div>
      <div className="page-head">
        <h1>Customers</h1>
        {data && <span className="muted">{data.total.toLocaleString()} accounts</span>}
      </div>

      <div className="filters card">
        <label>
          Segment
          <select value={segment} onChange={(e) => setSegment(e.target.value)}>
            {SEGMENTS.map((s) => (
              <option key={s} value={s}>
                {s ? `${s} · ${segmentName(s)}` : "All segments"}
              </option>
            ))}
          </select>
        </label>
        <label>
          Min LTV
          <input type="number" placeholder="0" value={minLtv} onChange={(e) => setMinLtv(e.target.value)} />
        </label>
        <label>
          Max churn (0–1)
          <input
            type="number" step="0.05" min="0" max="1" placeholder="1.0"
            value={maxChurn} onChange={(e) => setMaxChurn(e.target.value)}
          />
        </label>
      </div>

      {isError && <div className="card error">Failed to load: {(error as Error).message}</div>}

      <div className="card table-card">
        <table>
          <thead>
            <tr>
              <th>Customer</th><th>Email</th><th>Country</th><th>Segment</th>
              <th className="num">LTV</th><th className="num">Churn</th>
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i} className="skeleton-row">
                  <td colSpan={6}><div className="skeleton" /></td>
                </tr>
              ))}
            {data?.items.map((c) => (
              <tr key={c.customer_id} className="row-link" onClick={() => navigate(`/customers/${c.customer_id}`)}>
                <td>
                  <div className="cell-strong">{c.first_name} {c.last_name}</div>
                  <div className="muted mono">{c.customer_id}</div>
                </td>
                <td className="muted">{c.email}</td>
                <td>{c.country}</td>
                <td><span className="badge">{segmentName(c.segment_id)}</span></td>
                <td className="num">{currency(c.lifetime_value)}</td>
                <td className="num"><span className={`churn ${churnTone(c.churn_score)}`}>{pct(c.churn_score)}</span></td>
              </tr>
            ))}
            {data && data.items.length === 0 && (
              <tr><td colSpan={6} className="muted center">No customers match these filters.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="pager">
        <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>‹ Prev</button>
        <span className="muted">Page {page} / {totalPages}</span>
        <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next ›</button>
      </div>
    </div>
  );
}
