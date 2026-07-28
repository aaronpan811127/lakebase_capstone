"""Forward-ETL job control (T7) — SP client.

The Reports page triggers the dedup-into-gold job (Pattern B: Lakehouse Sync
replicates staging → lb_*_history SCD2; this job dedups the surviving PKs into
gold.customer_notes). Uses the app service principal.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.auth import sp_client
from backend.models import RunOut
from backend.settings import settings

log = logging.getLogger("customer360.jobs")
router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _life(state) -> str:
    lcs = getattr(state, "life_cycle_state", None)
    return getattr(lcs, "value", None) or (str(lcs).split(".")[-1] if lcs else "")


def _result(state) -> str | None:
    rs = getattr(state, "result_state", None)
    return getattr(rs, "value", None) or (str(rs).split(".")[-1] if rs else None)


@router.post("/run-forward-etl", response_model=RunOut, operation_id="runForwardEtl")
def run_forward_etl():
    if not settings.forward_etl_job_id:
        raise HTTPException(503, "FORWARD_ETL_JOB_ID not configured")
    w = sp_client()
    run = w.jobs.run_now(job_id=int(settings.forward_etl_job_id))
    return RunOut(run_id=run.run_id, state="PENDING")


@router.get("/{run_id}", response_model=RunOut, operation_id="getForwardEtlRun")
def get_run(run_id: int):
    w = sp_client()
    r = w.jobs.get_run(run_id=run_id)
    return RunOut(
        run_id=run_id,
        state=_life(r.state),
        result_state=_result(r.state),
        run_page_url=r.run_page_url,
        start_time=r.start_time,
        end_time=r.end_time,
    )


@router.get("/recent/list", response_model=list[RunOut], operation_id="listForwardEtlRuns")
def recent_runs(limit: int = 10):
    if not settings.forward_etl_job_id:
        return []
    w = sp_client()
    runs = w.jobs.list_runs(job_id=int(settings.forward_etl_job_id), limit=limit)
    out: list[RunOut] = []
    for r in runs:
        out.append(RunOut(
            run_id=r.run_id, state=_life(r.state), result_state=_result(r.state),
            run_page_url=r.run_page_url, start_time=r.start_time, end_time=r.end_time,
        ))
    return out
