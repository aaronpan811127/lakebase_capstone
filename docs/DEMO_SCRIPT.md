# Customer 360 — 3-minute demo script

**Record with:** macOS Cmd+Shift+5 → "Record Selected Portion" over the browser window.
**App URL:** https://customer360-7474659854906313.aws.databricksapps.com
**Before you hit record:** log in once, hard-refresh (Cmd+Shift+R) so the latest bundle loads,
and pick a customer to focus on (e.g. **C0003600 — James Chen**).

Target ~3:00. Times are cumulative.

---

### 0:00 — Intro (say while the Customers list is on screen)
> "This is Customer 360 — a customer-success app on Databricks Apps, backed by
> Lakebase. It's deployed as a git-source app. Here's the customer list —
> 10,000 accounts, served from a Lakebase synced table with server-side
> pagination and filtering."
- Action: show the list. Type in **Min LTV** (e.g. `50000`) and pick a **Segment**
  to show filtering; clear it.
- Toggle **light/dark** (top-right ☀️/🌙) once to show theming.

### 0:30 — Customer detail (tabs)
> "Clicking a row opens the 360 view. The tabs fan out their fetches in parallel."
- Action: click **James Chen (C0003600)**. Walk the tabs:
  - **Profile** — contact, segment, churn.
  - **Metrics** — "these lifetime/30/90-day spend, tickets and CSAT numbers are
    computed live across gold tables via the **SQL warehouse using my identity (OBO)**."
  - **Activity** — last 20 transactions.

### 1:15 — Writes (notes + segment override)
> "Reps can leave notes and override segments — these write to Lakebase staging
> tables transactionally, with an audit-log row for every write."
- Action: **Notes** tab → type a note → **Add note** → show it appears with author + timestamp.
- **Segment** tab → pick a segment + reason → **Apply override** → show "Saved · idempotent upsert".

### 1:50 — Genie
> "The floating Genie button answers ad-hoc questions in plain English, using
> the Genie Conversation API — also on my identity via OBO."
- Action: click the **✦** button bottom-right → ask *"How many customers are there?"*
  → show the answer, the generated SQL, and the result. (Optional: try the enlarge toggle.)

### 2:20 — Dashboard
> "The Dashboard tab embeds the AI/BI dashboard directly in the app via iframe."
- Action: click **Dashboard** in the sidebar → let the embedded dashboard render.

### 2:40 — Reports / forward-ETL
> "And Reports triggers the forward-ETL job that promotes staged notes and
> overrides into Delta gold — here's a run and its status, with recent-run history."
- Action: click **Reports** → **▶ Run forward-ETL** → show the status pill go to
  RUNNING, and the recent-runs table.

### ~3:00 — Close
> "Everything runs as the app service principal for Lakebase, and on the caller's
> identity via OBO for the warehouse and Genie. Deployed as a git-source app
> through Databricks Asset Bundles."

---

**Tips**
- If Genie takes a few seconds, that's the poll loop — the typing indicator shows.
- If the Dashboard iframe is slow, give it a beat before moving on.
- Keep the window at a normal desktop width so the sidebar + content both show.
