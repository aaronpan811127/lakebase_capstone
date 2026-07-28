# Customer 360 — Capstone Submission

A customer-success web app for Acme Retail: React + FastAPI on Databricks Apps,
backed by Lakebase (synced reads + staging writes) and the SQL warehouse
(OBO metrics + external M2M).

- **Repo:** https://github.com/jnshubham-db/gdc-apps-lakebase-capstone (branch `feat/customer360-app`)
- **App:** `customer360` (deploy via `databricks bundle run customer360 --target prod`)
- **Workspace:** `fe-sandbox-lakebase-capstone` · catalog `lakebase_capstone_catalog.gold` · Lakebase `capstone-pg`

---

## Task status

| Task | What | Status |
|---|---|---|
| T1 | Reverse ETL: 3 synced tables + 3 staging tables | ✅ (notebook 03 + `resources/lakebase.yml`) |
| T2 | OBO + SP auth; `lakebase_sp()` pool w/ token rotation | ✅ verified (`SELECT 1`, OBO current-user) |
| T3 | Customers list/detail (SP), metrics (OBO warehouse), notes+segment writes | ✅ verified live |
| T3a | External M2M endpoint + `_token.py` / `m2m_test.py` | ✅ endpoint verified (401→200); live M2M run needs deployed app |
| T4 | Dashboard embed | ✅ iframe renders w/ correct embed URL |
| T5 | Genie conversation endpoints + floating widget | ✅ verified end-to-end (answer + SQL + rows) |
| T6 | `app.yaml` (env, command, OBO scopes) | ✅ |
| T7 | Forward-ETL (Lakehouse Sync Pattern B) + dedup job + jobs API | ✅ code + notebooks; live run after deploy |
| T8 | DABs git-source app + resources | ✅ `bundle validate --target prod` passes |
| T9 | Branch+PITR, query insights | ✅ done live — see `docs/T9_lakebase_ops.md` |

---

## Reflection — sync-mode choices

- **`customers_synced` — CONTINUOUS.** The customer list/detail is the app's
  primary read path; reps expect edits upstream (LTV, churn recompute, segment)
  to appear within seconds. Continuous keeps Lakebase within seconds of gold.
- **`transactions_synced` — CONTINUOUS.** The Activity tab is a recent-activity
  feed; new transactions should show up promptly, so continuous is warranted
  despite the higher row volume (~100k).
- **`products_synced` — TRIGGERED (hourly).** The 200-row product catalog is
  slow-changing; paying for continuous replication buys nothing. Triggered
  hourly is cheaper and freshness is more than adequate for category labels.

Support tickets and segments stay in **gold** (not synced) — the Metrics tab
joins `transactions × products × support_tickets` and is served by the **SQL
warehouse via OBO**, so warehouse RLS/audit reflect the calling user.

## Reflection — forward-ETL pattern

Chose **Pattern B (Lakehouse Sync)**: Lakebase natively replicates the writable
staging tables into UC-managed `lb_*_history` Delta tables as SCD2 (no external
pipeline/compute — powered by `wal2delta`). A small **dedup-into-gold** job
(`dedup_into_gold.py`) collapses the SCD2 history to the latest surviving row
per PK and `MERGE`s into `gold.customer_notes`. The Reports page triggers that
job via `POST /api/jobs/run-forward-etl`. Idempotent by construction — the MERGE
on `note_id` is a no-op when no new history rows exist.

---

## Optimizations implemented

**Pagination (server-side, always).** List endpoint takes `page`/`page_size`
(default 25, hard cap 100, `422` above), returns `{items,total,page,page_size}`,
never ships all 10k rows. `ORDER BY lifetime_value DESC, customer_id` for a
stable sort. _Verified: `/api/customers?page_size=2` → 2 items, total 10000._

**Caching.**
- Server: `/api/config` cached with `cachetools.TTLCache(ttl=300)`.
- Client: TanStack Query per-key staleTimes — list 10s, detail 30s, metrics 60s,
  config/segments 5m; `invalidateQueries` after writes for instant refresh;
  `placeholderData: (prev) => prev` for flicker-free pagination.

**Connection pooling (Lakebase).** `psycopg_pool.AsyncConnectionPool` (min 2,
max 10). Lakebase OAuth tokens expire ~1h, so a `_TokenAuthConnection` subclass
mints a fresh token as the connection password on **every** connect, and
`max_lifetime=45m` recycles connections before expiry.

**React performance.** Routes code-split with `React.lazy` + `<Suspense>`
(verified: separate Customers/CustomerDetail/Dashboard/Reports chunks in the
build). Detail tabs fan out Profile/Metrics/Notes/Segment fetches in parallel.
Filter inputs debounced 250ms.

**API hygiene.** `GZipMiddleware(minimum_size=1000)`; Pydantic response models
(enforced + OpenAPI-documented); minimal projections (no `SELECT *` on the list);
warehouse/Genie calls use `wait_timeout="30s"`.

**Observability.** JSON structured logging; per-request `X-Request-Id`
middleware (generated if absent, echoed back); slow requests (>500ms) logged at
WARNING.

### What I'd add next
- Keyset (cursor) pagination once past a few thousand rows — replace `OFFSET`
  with `WHERE lifetime_value < :last_seen`.
- Composite Lakebase index on `(segment_id, lifetime_value DESC)` for filtered
  list queries.
- `Cache-Control: private, max-age=…` on idempotent GETs for free back-nav.
- Optimistic updates on note add / segment override.

---

## T3a — M2M test output

`examples/m2m_test.py` runs the SP `client_credentials` flow → OAuth bearer →
`GET /api/external/customers/{id}` against the deployed app. Locally the
endpoint was verified: **401 without a bearer, 200 + customer JSON with an OBO
token** (reads gold via the warehouse, never Lakebase/SP fallback). The full
deployed-app M2M run is pending T8 deploy + SP grants (CAN_USE on the app,
warehouse + gold SELECT on the SP) — paste `m2m_test.py` stdout here after.

```
# (paste examples/m2m_test.py output after deploy)
```

---

## T9 results (measured live)

- **Branch isolation:** branched `capstone-pg` → `capstone-pg-branch`,
  `DELETE FROM customer_notes_staging` on the branch left the parent unchanged
  (parent 1 → 1, branch 1 → 0). PITR restore procedure documented.
- **Query insights:** `idx_audit_actor` on `customer_audit_log(actor_email)`
  switched Seq Scan → Bitmap Heap Scan; server-side exec **p95 8.13ms → 1.55ms
  (5.3× faster)**.

Full detail + screenshot placeholders: `docs/T9_lakebase_ops.md`.

---

## Deploy (T8) — remaining manual steps

These require workspace-admin actions and are documented in
`capstone-scaffold/resources/app.yml`:

1. `databricks bundle deploy --target prod --profile lakebase-capstone`
2. Register a GitHub credential bound to the app SP (`git-credentials create`
   with `principal_id` = app `service_principal_id`).
3. `databricks bundle run customer360 --target prod` → pulls latest commit,
   restarts the app; Deployments tab should show the matching commit SHA.
4. Grant the app SP CAN_USE on the app + warehouse/gold SELECT, then run
   `examples/m2m_test.py`.
5. Workspace toggles: **User authorization (preview)** ON (OBO); allowlist the
   app host under **Embed Dashboard** (T4).
