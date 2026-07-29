# Customer 360 — Capstone Submission

A customer-success web app for Acme Retail: React + FastAPI on Databricks Apps,
backed by Lakebase (synced reads + staging writes) and the SQL warehouse
(OBO metrics + external M2M).

- **Repo:** https://github.com/aaronpan811127/lakebase_capstone (branch `feat/customer360-app`)
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
| T7 | Forward-ETL (Pattern A: psycopg + MERGE) + job + jobs API | ✅ verified — live run promotes staging → gold, idempotent |
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

Chose **Pattern A (psycopg + MERGE INTO Delta)**. A serverless notebook job
(`lakebase/forward_etl/pattern_a_psycopg/merge_into_gold.py`) connects to
Lakebase via psycopg, reads `*_staging WHERE processed = false`, builds a Spark
DataFrame, `MERGE`s it into `gold.customer_notes` / `gold.customer_segment_overrides`
(keyed on `note_id` / `customer_id`), then sets `processed = true` on the staged
rows. The Reports page triggers it via `POST /api/jobs/run-forward-etl`.
Idempotent by construction — only `processed = false` rows are read and the MERGE
keys on the PK, so re-running with no new staged rows is a no-op.

Verified live (serverless run, deps via the job `environments` spec — psycopg +
databricks-sdk — not in-notebook `%pip`): a run promoted **3 notes + 1 override**
into gold (`gold.customer_notes=3`, `gold.customer_segment_overrides=1`, confirmed
by warehouse query), flipped all staged rows to `processed=true`, and a second run
was a clean no-op (0 unprocessed). Screenshots of the promoted rows in Catalog
Explorer: `docs/t7_screenshots/` (`gold.customer_notes` overview + sample,
`gold.customer_segment_overrides` sample).

**Why not Pattern B (Lakehouse Sync / Lakebase CDF):** that feature requires an
**Autoscaling Postgres 17** instance and is UI-only Public Preview; `capstone-pg`
is **provisioned Postgres 16**, so CDF cannot be enabled on it (verified via
`get_database_instance` → `pg_version: PG_VERSION_16`, and the SDK/CLI/REST expose
no CDF enablement path). Pattern A needs no extra Databricks feature and runs on
the existing instance.

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

## T3a — M2M test output (against the deployed app)

`examples/m2m_test.py` runs the SP `client_credentials` flow → OAuth bearer →
`GET /api/external/customers/{id}` against the **deployed** app. The Apps proxy
validates the bearer and forwards `X-Forwarded-Access-Token`; the handler reads
gold via the SQL warehouse as the caller (never Lakebase, never app-SP fallback).

```
→ minting OAuth bearer via client_credentials for SP 439c27fa-1aba-4091-939a-5d7a5f303289
  bearer acquired: eyJraWQiOiJqblJx… (828 chars)
→ GET https://customer360-7474659854906313.aws.databricksapps.com/api/external/customers/C0003600
← HTTP 200
{
  "customer_id": "C0003600",
  "first_name": "James", "last_name": "Chen",
  "email": "james.chen3600@example.com", "country": "GB", "city": "New York",
  "segment_id": "S5", "lifetime_value": 69000.23, "churn_score": 0.506,
  "recent_transactions": [ … 10 items … ]
}

PASS: 200 + customer JSON (10 recent transactions)
```

Setup for the run: minted an OAuth secret for the app SP
(`service-principal-secrets-proxy create`), granted the SP **CAN_USE on the
app** + **CAN_USE on the warehouse** + **USE CATALOG / USE SCHEMA / SELECT** on
`lakebase_capstone_catalog.gold`.

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

## Deploy (T8) — ✅ DEPLOYED & VERIFIED

**Live app:** https://customer360-7474659854906313.aws.databricksapps.com — state
`RUNNING`, deployment `SUCCEEDED`.

1. ✅ `databricks bundle deploy --target prod` — app, forward-ETL job, 3 synced tables.
2. ✅ GitHub credential bound to the app SP (`git-credentials create`,
   `principal_id=78783178816599`) — git-source pull works.
3. ✅ `databricks bundle run customer360 --target prod` — **git-source app**:
   `git_source.resolved_commit` matches local HEAD, `source_code_path
   capstone-scaffold/app`, branch `feat/customer360-app` (not a workspace upload).
4. ✅ Granted the app SP Lakebase role (`439c27fa-…`) SELECT on synced tables +
   SELECT/INSERT/UPDATE on staging + `ALTER DEFAULT PRIVILEGES`; CAN_USE on app +
   warehouse + gold SELECT for M2M.

**Verified on the deployed app** (through the Apps proxy, real OBO headers):
`/api/health` 200 · SPA index 200 · `/api/customers` (10k, SP) · detail + txns ·
`/api/customers/{id}/metrics` (warehouse OBO) · note write + audit · idempotent
segment override · Genie start (OBO) · external M2M 401→200.

### Root-cause notes (bugs found & fixed via live deploy)
- **uv.lock pinned an internal index.** The developer's global uv config uses
  `pypi-proxy.dev.databricks.com` as default index, so `uv lock` baked that
  unreachable-from-build host into the lock → `uv sync` timed out per-wheel.
  Fixed by pinning `pypi.org` in `pyproject.toml` and rewriting the lock URLs to
  public PyPI / `files.pythonhosted.org`.
- **OBO client double-auth.** In the Apps runtime the env carries the SP's OAuth
  creds, so `WorkspaceClient(token=…)` raised "more than one authorization
  method configured". Fixed with `auth_type="pat"` in `obo_client`.
- **App SP had no Lakebase grants** (fresh PG role) — ran the T1 grant step.

### Remaining (manual / recording)
- Workspace toggles: **User authorization (preview)** ON (OBO consent);
  allowlist the app host under **Embed Dashboard** (T4) if the iframe is blocked.
- T9 UI screenshots; 3-min demo recording.

> **Reminder:** rotate/revoke the GitHub PAT (git credential) **and** the app-SP
> OAuth secret minted for the M2M test — both appeared in shell transcripts.
