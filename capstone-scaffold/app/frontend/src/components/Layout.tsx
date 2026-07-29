import { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/api/client";
import type { MeOut } from "@/api/types";
import GenieWidget from "@/components/GenieWidget";
import { useTheme } from "@/hooks/theme";

const NAV = [
  { to: "/customers", label: "Customers", icon: "👥" },
  { to: "/dashboard", label: "Dashboard", icon: "📊" },
  { to: "/reports", label: "Reports", icon: "⚙️" },
];

export default function Layout({ children }: { children: ReactNode }) {
  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: () => apiGet<MeOut>("/api/me"),
    staleTime: 5 * 60_000,
  });
  const workspace = me?.workspace_host?.replace(/^https?:\/\//, "").split(".")[0] ?? "workspace";
  const [theme, toggleTheme] = useTheme();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">◆</span>
          <div>
            <div className="brand-title">Customer 360</div>
            <div className="brand-sub">Acme Retail</div>
          </div>
        </div>
        <nav>
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}
            >
              <span className="nav-icon">{n.icon}</span>
              {n.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="topbar-spacer" />
          <div className="topbar-right">
            <button
              className="theme-toggle"
              onClick={toggleTheme}
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              aria-label="Toggle theme"
            >
              {theme === "dark" ? "☀️" : "🌙"}
            </button>
            <span className="ws-badge">{workspace}</span>
            <span className="user-email">{me?.email ?? "…"}</span>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>

      <GenieWidget />
    </div>
  );
}
