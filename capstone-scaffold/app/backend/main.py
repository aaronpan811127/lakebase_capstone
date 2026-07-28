"""Customer 360 FastAPI app.

Serves the built React SPA (from ``backend/static``) and the ``/api/*`` surface:
Lakebase synced reads (SP), SQL-warehouse aggregates (OBO), Genie (OBO),
staging writes (SP), external M2M reads (OBO), and forward-ETL job control (SP).
"""
from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)
log = logging.getLogger("customer360")

app = FastAPI(title="Customer 360", version="0.1.0")
app.add_middleware(GZipMiddleware, minimum_size=1000)

STATIC_DIR = Path(__file__).parent / "static"


@app.middleware("http")
async def request_id_and_timing(request: Request, call_next):
    """Attach a correlation id and log slow requests."""
    req_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-Id"] = req_id
    if elapsed_ms > 500:
        log.warning("slow request %s %s %.0fms", request.method, request.url.path, elapsed_ms)
    return response


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── routers ───────────────────────────────────────────────────────────────
from backend.routers import config as config_router  # noqa: E402
from backend.routers import customers as customers_router  # noqa: E402
from backend.routers import external as external_router  # noqa: E402
from backend.routers import genie as genie_router  # noqa: E402
from backend.routers import jobs as jobs_router  # noqa: E402

app.include_router(config_router.router)
app.include_router(customers_router.router)
app.include_router(external_router.router)
app.include_router(genie_router.router)
app.include_router(jobs_router.router)


# ── static SPA (mounted last so /api/* wins) ────────────────────────────────
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        index = STATIC_DIR / "index.html"
        if index.is_file():
            return FileResponse(index)
        return JSONResponse({"detail": "frontend not built"}, status_code=404)
