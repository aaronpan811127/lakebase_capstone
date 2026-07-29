"""Authentication helpers.

Two identities per the capstone auth model:

* **OBO** — ``obo_client(request)`` builds a WorkspaceClient from the caller's
  ``X-Forwarded-Access-Token`` (injected by the Apps proxy). Used for SQL
  warehouse aggregates, Genie, and the external M2M surface, so warehouse
  RLS / audit reflect the *calling* identity.
* **SP** — ``sp_client()`` is the app's service-principal client (default SDK
  auth from the Apps runtime). Used for all Lakebase access and job triggers.

There is intentionally no ``lakebase_obo()``: Lakebase does not yet support OBO
``postgres`` scopes, so every DB read/write runs as the SP and records the
calling user (``actor_email``) for the audit log.
"""
from __future__ import annotations

from functools import lru_cache

from databricks.sdk import WorkspaceClient
from fastapi import HTTPException, Request

from backend.settings import settings

OBO_HEADER = "X-Forwarded-Access-Token"
EMAIL_HEADER = "X-Forwarded-Email"


def obo_client(request: Request) -> WorkspaceClient:
    """WorkspaceClient carrying the calling user's identity (OBO)."""
    token = request.headers.get(OBO_HEADER)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing X-Forwarded-Access-Token (OBO not authorized for this request)",
        )
    # Force PAT-only auth. In the Apps runtime the environment also carries the
    # SP's OAuth creds (DATABRICKS_CLIENT_ID/SECRET); without auth_type="pat" the
    # SDK sees both the OBO token and ambient OAuth and raises "more than one
    # authorization method configured".
    return WorkspaceClient(
        host=settings.databricks_host or None,
        token=token,
        auth_type="pat",
    )


@lru_cache(maxsize=1)
def sp_client() -> WorkspaceClient:
    """App service-principal client (default runtime auth). Cached process-wide."""
    return WorkspaceClient()


def actor_email(request: Request) -> str:
    """Calling user's email from the Apps proxy header, for the audit log."""
    return request.headers.get(EMAIL_HEADER) or "unknown"
