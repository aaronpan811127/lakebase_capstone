import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  useCustomer,
  useMetrics,
  useNotes,
  useSegmentOverride,
  useAddNote,
  useOverrideSegment,
} from "@/hooks/customers";
import { currency, num, pct, segmentName, churnTone, SEGMENT_NAMES } from "@/lib/format";
import type { TransactionOut } from "@/api/types";

type Tab = "profile" | "metrics" | "activity" | "notes" | "segment";
const TABS: { id: Tab; label: string }[] = [
  { id: "profile", label: "Profile" },
  { id: "metrics", label: "Metrics" },
  { id: "activity", label: "Activity" },
  { id: "notes", label: "Notes" },
  { id: "segment", label: "Segment" },
];

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="field-label">{label}</div>
      <div className="field-value">{value ?? "—"}</div>
    </div>
  );
}

export default function CustomerDetail() {
  const { id = "" } = useParams();
  const [tab, setTab] = useState<Tab>("profile");

  // Fan out fetches in parallel — each tab's data loads independently.
  const customer = useCustomer(id);
  const metrics = useMetrics(id);
  const notes = useNotes(id);
  const segment = useSegmentOverride(id);

  const c = customer.data;
  const initials = c ? `${c.first_name[0] ?? ""}${c.last_name[0] ?? ""}` : "··";

  return (
    <div>
      <div className="detail-head">
        <Link to="/customers" className="back-link">‹ Customers</Link>
      </div>

      {customer.isError && (
        <div className="card error">Failed to load customer: {(customer.error as Error).message}</div>
      )}

      <div className="detail-head">
        <div className="avatar">{initials.toUpperCase()}</div>
        <div>
          <h1>{c ? `${c.first_name} ${c.last_name}` : "Loading…"}</h1>
          <div className="muted mono">{id}</div>
        </div>
        {c && (
          <div style={{ marginLeft: "auto", display: "flex", gap: 10, alignItems: "center" }}>
            <span className="badge">{segmentName(c.segment_id)}</span>
            <span className={`churn ${churnTone(c.churn_score)}`}>churn {pct(c.churn_score)}</span>
          </div>
        )}
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={"tab" + (tab === t.id ? " active" : "")}
            onClick={() => setTab(t.id)}
          >
            {t.label}
            {t.id === "notes" && notes.data ? ` (${notes.data.length})` : ""}
          </button>
        ))}
      </div>

      {tab === "profile" && (
        <div className="card">
          {c ? (
            <div className="field-grid">
              <Field label="Email" value={c.email} />
              <Field label="Phone" value={c.phone} />
              <Field label="Country" value={c.country} />
              <Field label="City" value={c.city} />
              <Field label="Age" value={c.age} />
              <Field label="Gender" value={c.gender} />
              <Field label="Signup date" value={c.signup_date} />
              <Field label="Last purchase" value={c.last_purchase_date} />
              <Field label="Segment" value={`${c.segment_id} · ${segmentName(c.segment_id)}`} />
              <Field label="Lifetime value" value={currency(c.lifetime_value)} />
              <Field label="Churn score" value={pct(c.churn_score)} />
            </div>
          ) : (
            <div className="muted">Loading profile…</div>
          )}
        </div>
      )}

      {tab === "metrics" && (
        <div>
          {metrics.isLoading && <div className="card muted">Computing metrics via SQL warehouse…</div>}
          {metrics.isError && (
            <div className="card error">Metrics unavailable: {(metrics.error as Error).message}</div>
          )}
          {metrics.data && (
            <>
              <div className="metric-row">
                <div className="metric-tile">
                  <div className="val">{currency(metrics.data.lifetime_spend)}</div>
                  <div className="lbl">Lifetime spend</div>
                </div>
                <div className="metric-tile">
                  <div className="val">{currency(metrics.data.last_30d_spend)}</div>
                  <div className="lbl">Last 30 days</div>
                </div>
                <div className="metric-tile">
                  <div className="val">{currency(metrics.data.last_90d_spend)}</div>
                  <div className="lbl">Last 90 days</div>
                </div>
                <div className="metric-tile">
                  <div className="val">{metrics.data.open_tickets}</div>
                  <div className="lbl">Open tickets</div>
                </div>
                <div className="metric-tile">
                  <div className="val">{metrics.data.avg_csat != null ? metrics.data.avg_csat.toFixed(1) : "—"}</div>
                  <div className="lbl">Avg CSAT</div>
                </div>
              </div>
              <div className="card">
                <h2>Top categories</h2>
                {metrics.data.top_categories.length === 0 && <div className="muted">No completed purchases.</div>}
                {(() => {
                  const max = Math.max(1, ...metrics.data!.top_categories.map((x) => x.spend));
                  return metrics.data!.top_categories.map((cat) => (
                    <div className="cat-bar" key={cat.category}>
                      <div className="name">{cat.category}</div>
                      <div className="track"><div className="fill" style={{ width: `${(cat.spend / max) * 100}%` }} /></div>
                      <div className="amt">{currency(cat.spend)}</div>
                    </div>
                  ));
                })()}
              </div>
            </>
          )}
        </div>
      )}

      {tab === "activity" && (
        <div className="card table-card">
          <table>
            <thead>
              <tr>
                <th>Transaction</th><th>Product</th><th>Date</th><th>Channel</th><th>Status</th>
                <th className="num">Amount</th>
              </tr>
            </thead>
            <tbody>
              {customer.isLoading && (
                <tr className="skeleton-row"><td colSpan={6}><div className="skeleton" /></td></tr>
              )}
              {c?.recent_transactions.map((t: TransactionOut) => (
                <tr key={t.transaction_id}>
                  <td className="mono">{t.transaction_id}</td>
                  <td className="mono">{t.product_id}</td>
                  <td>{t.transaction_date}</td>
                  <td>{t.channel}</td>
                  <td><span className="badge">{t.status}</span></td>
                  <td className="num">{currency(t.amount)}</td>
                </tr>
              ))}
              {c && c.recent_transactions.length === 0 && (
                <tr><td colSpan={6} className="muted center">No recent transactions.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === "notes" && <NotesTab id={id} notes={notes} />}
      {tab === "segment" && <SegmentTab id={id} currentSegment={c?.segment_id} override={segment} />}
    </div>
  );
}

function NotesTab({
  id,
  notes,
}: {
  id: string;
  notes: ReturnType<typeof useNotes>;
}) {
  const [text, setText] = useState("");
  const addNote = useAddNote(id);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    addNote.mutate(text.trim(), { onSuccess: () => setText("") });
  };

  return (
    <div className="card">
      <form className="form-field" onSubmit={submit}>
        <label>Add a note</label>
        <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Customer called about…" />
        <div className="form-row">
          <button type="submit" className="primary" disabled={addNote.isPending || !text.trim()}>
            {addNote.isPending ? "Saving…" : "Add note"}
          </button>
          {addNote.isError && <span className="error">{(addNote.error as Error).message}</span>}
        </div>
      </form>

      <div style={{ marginTop: 8 }}>
        {notes.isLoading && <div className="muted">Loading notes…</div>}
        {notes.data?.length === 0 && <div className="muted">No notes yet.</div>}
        {notes.data?.map((n) => (
          <div className="note-item" key={n.note_id}>
            <div>{n.note_text}</div>
            <div className="note-meta">
              <span>{n.author_email}</span>
              <span>·</span>
              <span>{new Date(n.created_at).toLocaleString()}</span>
              {!n.processed && <span className="pill warn">pending ETL</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SegmentTab({
  id,
  currentSegment,
  override,
}: {
  id: string;
  currentSegment?: string;
  override: ReturnType<typeof useSegmentOverride>;
}) {
  const [seg, setSeg] = useState("");
  const [reason, setReason] = useState("");
  const mut = useOverrideSegment(id);
  const current = override.data;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!seg) return;
    mut.mutate({ override_segment: seg, reason: reason || undefined });
  };

  return (
    <div className="card">
      <div className="field-grid" style={{ marginBottom: 20 }}>
        <Field label="System segment" value={currentSegment ? `${currentSegment} · ${segmentName(currentSegment)}` : "—"} />
        <Field
          label="Current override"
          value={current ? `${current.override_segment} · ${segmentName(current.override_segment)}` : "None"}
        />
        {current && <Field label="Override reason" value={current.reason} />}
        {current && <Field label="Set by" value={current.author_email} />}
      </div>

      <form onSubmit={submit}>
        <div className="form-field">
          <label>Override segment</label>
          <select value={seg} onChange={(e) => setSeg(e.target.value)}>
            <option value="">Select segment…</option>
            {Object.keys(SEGMENT_NAMES).map((s) => (
              <option key={s} value={s}>{s} · {SEGMENT_NAMES[s]}</option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <label>Reason (optional)</label>
          <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why override?" />
        </div>
        <div className="form-row">
          <button type="submit" className="primary" disabled={mut.isPending || !seg}>
            {mut.isPending ? "Saving…" : "Apply override"}
          </button>
          {mut.isSuccess && <span className="success-flash">Saved · idempotent upsert</span>}
          {mut.isError && <span className="error">{(mut.error as Error).message}</span>}
        </div>
      </form>
    </div>
  );
}
