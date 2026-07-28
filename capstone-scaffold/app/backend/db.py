"""Lakebase (Postgres) access as the app service principal.

A single async connection pool per worker. Lakebase OAuth tokens expire (~1h),
so we mint a fresh token via ``generate_database_credential`` and inject it as
the connection password on **every connect** through a custom
``AsyncConnection`` subclass. This is the runtime-safe path — the notebook's
``w.config.oauth_token()`` does NOT work off-driver.

Usage::

    async with lakebase_sp() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1")
"""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from functools import lru_cache

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from backend.auth import sp_client
from backend.settings import settings

log = logging.getLogger("customer360.db")

_POOL: AsyncConnectionPool | None = None


@lru_cache(maxsize=1)
def _pg_user() -> str:
    """The SP's identity is the Postgres role name (its client_id / user_name)."""
    return sp_client().current_user.me().user_name


def _fresh_token() -> str:
    """Mint a short-lived Lakebase OAuth token for the configured instance."""
    cred = sp_client().database.generate_database_credential(
        request_id=str(uuid.uuid4()),
        instance_names=[settings.pg_instance_name],
    )
    return cred.token


class _TokenAuthConnection(AsyncConnection):
    """AsyncConnection that injects a freshly-minted Lakebase token as password."""

    @classmethod
    async def connect(cls, conninfo: str = "", **kwargs):
        kwargs["password"] = _fresh_token()
        return await super().connect(conninfo, **kwargs)


def _conninfo() -> str:
    return (
        f"host={settings.pghost} port=5432 dbname={settings.pgdatabase} "
        f"user={_pg_user()} sslmode=require"
    )


async def _configure(conn: AsyncConnection) -> None:
    conn.row_factory = dict_row


def build_pool() -> AsyncConnectionPool:
    """Construct (but do not open) the pool. Token injected per connect."""
    return AsyncConnectionPool(
        conninfo=_conninfo(),
        min_size=2,
        max_size=10,
        open=False,
        configure=_configure,
        connection_class=_TokenAuthConnection,
        max_lifetime=45 * 60,  # recycle before the ~1h token expiry
        reconnect_timeout=30,
    )


async def get_pool() -> AsyncConnectionPool:
    global _POOL
    if _POOL is None:
        _POOL = build_pool()
        await _POOL.open(wait=True, timeout=30)
        log.info("lakebase pool opened host=%s db=%s", settings.pghost, settings.pgdatabase)
    return _POOL


@asynccontextmanager
async def lakebase_sp():
    """Yield a pooled Lakebase connection authenticated as the app SP."""
    pool = await get_pool()
    async with pool.connection() as conn:
        yield conn


async def close_pool() -> None:
    global _POOL
    if _POOL is not None:
        await _POOL.close()
        _POOL = None
