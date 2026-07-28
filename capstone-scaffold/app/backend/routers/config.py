"""Config + identity endpoints (T4 embed config + top-bar user)."""
from __future__ import annotations

from cachetools import TTLCache, cached
from fastapi import APIRouter, Request

from backend.auth import EMAIL_HEADER
from backend.models import ConfigOut, MeOut
from backend.settings import settings

router = APIRouter(prefix="/api", tags=["config"])

_config_cache: TTLCache = TTLCache(maxsize=1, ttl=300)


@cached(_config_cache)
def _config() -> ConfigOut:
    return ConfigOut(
        databricks_host=settings.databricks_host.rstrip("/"),
        dashboard_id=settings.dashboard_id,
        genie_space_id=settings.genie_space_id,
    )


@router.get("/config", response_model=ConfigOut, operation_id="getConfig")
def get_config():
    return _config()


@router.get("/me", response_model=MeOut, operation_id="getMe")
def get_me(request: Request):
    return MeOut(
        email=request.headers.get(EMAIL_HEADER) or "unknown",
        workspace_host=settings.databricks_host.rstrip("/"),
    )
