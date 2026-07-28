import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/client";
import type { ConfigOut } from "@/api/types";

export default function Dashboard() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["config"],
    queryFn: () => apiGet<ConfigOut>("/api/config"),
    staleTime: 5 * 60_000,
  });

  const src =
    data && `${data.databricks_host}/embed/dashboardsv3/${data.dashboard_id}`;

  return (
    <div>
      <div className="page-head">
        <h1>Dashboard</h1>
        <span className="muted">Segment LTV · top products · ticket trends · churn</span>
      </div>

      {isLoading && <div className="card muted">Loading dashboard config…</div>}
      {isError && <div className="card error">Failed to load config: {(error as Error).message}</div>}

      {src && (
        <div className="iframe-wrap">
          <iframe src={src} title="Customer 360 AI/BI Dashboard" />
        </div>
      )}
    </div>
  );
}
