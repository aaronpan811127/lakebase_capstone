import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/api/client";
import type { RunOut } from "@/api/types";

function stateTone(r: RunOut): string {
  const s = (r.result_state || r.state || "").toUpperCase();
  if (s === "SUCCESS") return "ok";
  if (["FAILED", "TIMEDOUT", "CANCELED", "CANCELLED"].includes(s)) return "danger";
  if (["RUNNING", "PENDING", "QUEUED"].includes(s)) return "running";
  return "warn";
}

function stateLabel(r: RunOut): string {
  return (r.result_state || r.state || "unknown").toUpperCase();
}

export default function Reports() {
  const qc = useQueryClient();
  const [activeRun, setActiveRun] = useState<number | null>(null);

  const recent = useQuery({
    queryKey: ["etl-runs"],
    queryFn: () => apiGet<RunOut[]>("/api/jobs/recent/list?limit=10"),
    staleTime: 10_000,
  });

  const runStatus = useQuery({
    queryKey: ["etl-run", activeRun],
    queryFn: () => apiGet<RunOut>(`/api/jobs/${activeRun}`),
    enabled: activeRun != null,
    refetchInterval: (q) => {
      const s = (q.state.data?.state || "").toUpperCase();
      return s && !["TERMINATED", "INTERNAL_ERROR", "SKIPPED"].includes(s) ? 2500 : false;
    },
  });

  // Stop polling + refresh history once the active run terminates.
  useEffect(() => {
    const s = (runStatus.data?.state || "").toUpperCase();
    if (s === "TERMINATED" || s === "INTERNAL_ERROR" || s === "SKIPPED") {
      qc.invalidateQueries({ queryKey: ["etl-runs"] });
    }
  }, [runStatus.data?.state, qc]);

  const trigger = useMutation({
    mutationFn: () => apiPost<RunOut>("/api/jobs/run-forward-etl"),
    onSuccess: (r) => {
      setActiveRun(r.run_id);
      qc.invalidateQueries({ queryKey: ["etl-runs"] });
    },
  });

  return (
    <div>
      <div className="page-head">
        <h1>Reports</h1>
        <span className="muted">Forward-ETL: staging → gold</span>
      </div>

      <div className="card">
        <h2>Run forward-ETL</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Promotes staged notes &amp; segment overrides into Delta gold. Idempotent — re-running
          with no new staging rows is a no-op.
        </p>
        <div className="form-row">
          <button className="primary" onClick={() => trigger.mutate()} disabled={trigger.isPending}>
            {trigger.isPending ? "Triggering…" : "▶ Run forward-ETL"}
          </button>
          {runStatus.data && (
            <span className={`pill ${stateTone(runStatus.data)}`}>
              run #{runStatus.data.run_id} · {stateLabel(runStatus.data)}
            </span>
          )}
          {runStatus.data?.run_page_url && (
            <a className="back-link" href={runStatus.data.run_page_url} target="_blank" rel="noreferrer">
              Open run ↗
            </a>
          )}
        </div>
        {trigger.isError && (
          <div className="error" style={{ marginTop: 10 }}>{(trigger.error as Error).message}</div>
        )}
      </div>

      <div className="card table-card">
        <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)" }}>
          <h2 style={{ margin: 0 }}>Recent runs</h2>
        </div>
        <table>
          <thead>
            <tr>
              <th>Run</th><th>State</th><th>Result</th><th>Started</th><th>Ended</th><th></th>
            </tr>
          </thead>
          <tbody>
            {recent.isLoading && (
              <tr className="skeleton-row"><td colSpan={6}><div className="skeleton" /></td></tr>
            )}
            {recent.data?.length === 0 && (
              <tr><td colSpan={6} className="muted center">No runs yet.</td></tr>
            )}
            {recent.data?.map((r) => (
              <tr key={r.run_id}>
                <td className="mono">#{r.run_id}</td>
                <td>{r.state}</td>
                <td><span className={`pill ${stateTone(r)}`}>{stateLabel(r)}</span></td>
                <td className="muted">{r.start_time ? new Date(r.start_time).toLocaleString() : "—"}</td>
                <td className="muted">{r.end_time ? new Date(r.end_time).toLocaleString() : "—"}</td>
                <td>
                  {r.run_page_url && (
                    <a className="back-link" href={r.run_page_url} target="_blank" rel="noreferrer">↗</a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
