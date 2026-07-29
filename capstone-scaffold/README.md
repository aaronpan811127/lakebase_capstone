# Customer 360 — build & deploy

FastAPI backend serving a built React SPA, deployed as a **git-source** Databricks
App. See `CAPSTONE_TASKS.md` for the full spec and `../SUBMISSION.md` for the writeup.

## Layout

```
app/
  backend/        FastAPI app (routers, auth, db, models)
  backend/static/ COMPILED React bundle — COMMITTED, served at runtime
  frontend/       React/Vite source
  app.yaml        Apps runtime config (T6)
resources/        DABs resources: app.yml, jobs.yml, lakebase.yml (T8)
databricks.yml    DABs bundle root
lakebase/         forward-ETL notebooks (T7)
```

## Local dev

```bash
# backend (from app/)
uv sync --extra dev
source .env && DATABRICKS_CONFIG_PROFILE=lakebase-capstone \
  uv run uvicorn backend.main:app --port 8000
# frontend (from app/frontend/) — proxies /api -> :8000
npm install && npm run dev            # http://localhost:5173
uv run pytest                          # 22 tests
```

## ⚠️ Building the frontend for deploy

The compiled bundle lives in **`backend/static/`** (outside `frontend/`) and is
what the deployed app serves. Vite renames hashed files each build, so
`git add frontend/` does **NOT** stage the output — commit UI changes that way and
the deployed app keeps serving a **stale bundle**.

**Always build for deploy with one of these (they build AND stage `backend/static`):**

```bash
cd app && ./build.sh
# or
cd app/frontend && npm run build:deploy
```

Then commit, push, and `bundle run` (below).

## Deploy (git-source app)

```bash
cd capstone-scaffold
databricks bundle validate --target prod --profile lakebase-capstone
databricks bundle deploy   --target prod --profile lakebase-capstone
databricks bundle run customer360 --target prod --profile lakebase-capstone
```

`bundle run` pulls the latest commit from the branch in `databricks.yml`
(`git_branch`) and restarts the app — so **push your commit before `bundle run`**.
Verify: `databricks apps get customer360` → `active_deployment.git_source.resolved_commit`
should equal your local `git rev-parse HEAD`.

First-time only: register a GitHub credential bound to the app SP
(`git-credentials create` with `principal_id` = app `service_principal_id`) and
grant the app SP its Lakebase/warehouse reads — see `resources/app.yml` and
`../SUBMISSION.md`.
