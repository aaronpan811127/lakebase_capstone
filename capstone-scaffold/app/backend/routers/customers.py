"""Customer read/write endpoints (T3).

* list + detail  → Lakebase synced tables via the app SP
* metrics        → gold via SQL warehouse using the caller's OBO bearer
* notes/segment  → transactional staging writes + audit, via the app SP
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Query, Request
from psycopg.rows import dict_row

from backend.auth import actor_email, obo_client
from backend.db import lakebase_sp
from backend.models import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    CategorySpend,
    CustomerDetailOut,
    CustomerListItem,
    CustomerListOut,
    MetricsOut,
    NoteIn,
    NoteOut,
    SegmentOverrideIn,
    SegmentOverrideOut,
    TransactionOut,
)
from backend.settings import settings

log = logging.getLogger("customer360.customers")
router = APIRouter(prefix="/api/customers", tags=["customers"])

_LIST_COLS = (
    "customer_id, first_name, last_name, email, country, "
    "segment_id, lifetime_value, churn_score"
)


def build_list_query(
    segment: str | None, min_ltv: float | None, max_churn: float | None,
    page: int, page_size: int,
) -> tuple[str, list, str, list]:
    """Return (data_sql, data_params, count_sql, count_params) — parametrized."""
    where: list[str] = []
    params: list = []
    if segment:
        where.append("segment_id = %s")
        params.append(segment)
    if min_ltv is not None:
        where.append("lifetime_value >= %s")
        params.append(min_ltv)
    if max_churn is not None:
        where.append("churn_score <= %s")
        params.append(max_churn)
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    offset = (page - 1) * page_size
    data_sql = (
        f"SELECT {_LIST_COLS} FROM customers_synced{clause} "
        f"ORDER BY lifetime_value DESC, customer_id LIMIT %s OFFSET %s"
    )
    data_params = [*params, page_size, offset]
    count_sql = f"SELECT COUNT(*) AS n FROM customers_synced{clause}"
    return data_sql, data_params, count_sql, list(params)


@router.get("", response_model=CustomerListOut, operation_id="listCustomers")
async def list_customers(
    segment: str | None = None,
    min_ltv: float | None = None,
    max_churn: float | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1),
):
    if page_size > MAX_PAGE_SIZE:
        raise HTTPException(422, f"page_size exceeds cap of {MAX_PAGE_SIZE}")
    data_sql, data_params, count_sql, count_params = build_list_query(
        segment, min_ltv, max_churn, page, page_size
    )
    async with lakebase_sp() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(count_sql, count_params)
            total = (await cur.fetchone())["n"]
            await cur.execute(data_sql, data_params)
            rows = await cur.fetchall()
    return CustomerListOut(
        items=[CustomerListItem(**r) for r in rows],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{customer_id}", response_model=CustomerDetailOut, operation_id="getCustomer")
async def get_customer(customer_id: str):
    async with lakebase_sp() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT customer_id, first_name, last_name, email, phone, country, city, "
                "age, gender, signup_date, last_purchase_date, segment_id, lifetime_value, "
                "churn_score FROM customers_synced WHERE customer_id = %s",
                (customer_id,),
            )
            cust = await cur.fetchone()
            if not cust:
                raise HTTPException(404, "customer not found")
            await cur.execute(
                "SELECT transaction_id, product_id, transaction_date, channel, status, amount "
                "FROM transactions_synced WHERE customer_id = %s "
                "ORDER BY transaction_date DESC LIMIT 20",
                (customer_id,),
            )
            txns = await cur.fetchall()
    return CustomerDetailOut(
        **cust, recent_transactions=[TransactionOut(**t) for t in txns]
    )


# ── metrics (SQL warehouse + OBO) ────────────────────────────────────────────
def build_metrics_sql(gold: str) -> str:
    """Single-round-trip aggregate across transactions × products × tickets."""
    return f"""
    WITH txn AS (
      SELECT t.amount, t.transaction_date, p.category
      FROM {gold}.transactions t
      JOIN {gold}.products p ON t.product_id = p.product_id
      WHERE t.customer_id = :cid AND t.status = 'completed'
    )
    SELECT
      (SELECT COALESCE(SUM(amount),0) FROM txn) AS lifetime_spend,
      (SELECT COALESCE(SUM(amount),0) FROM txn WHERE transaction_date >= current_date() - 30) AS last_30d,
      (SELECT COALESCE(SUM(amount),0) FROM txn WHERE transaction_date >= current_date() - 90) AS last_90d,
      (SELECT COUNT(*) FROM {gold}.support_tickets
         WHERE customer_id = :cid AND status IN ('open','in_progress')) AS open_tickets,
      (SELECT ROUND(AVG(csat_score),2) FROM {gold}.support_tickets
         WHERE customer_id = :cid AND csat_score IS NOT NULL) AS avg_csat
    """


def build_categories_sql(gold: str) -> str:
    return f"""
      SELECT p.category AS category, ROUND(SUM(t.amount),2) AS spend
      FROM {gold}.transactions t JOIN {gold}.products p ON t.product_id = p.product_id
      WHERE t.customer_id = :cid AND t.status = 'completed'
      GROUP BY p.category ORDER BY spend DESC LIMIT 5
    """


@router.get("/{customer_id}/metrics", response_model=MetricsOut, operation_id="getCustomerMetrics")
async def get_metrics(customer_id: str, request: Request):
    from databricks.sdk.service.sql import StatementParameterListItem

    w = obo_client(request)
    gold = settings.gold
    params = [StatementParameterListItem(name="cid", value=customer_id)]

    def run(sql: str):
        return w.statement_execution.execute_statement(
            warehouse_id=settings.warehouse_id, statement=sql,
            parameters=params, wait_timeout="30s",
        )

    agg = run(build_metrics_sql(gold))
    cats = run(build_categories_sql(gold))

    row = (agg.result.data_array or [[0, 0, 0, 0, None]])[0]
    lifetime, l30, l90, open_t, csat = row[0], row[1], row[2], row[3], row[4]
    cat_rows = cats.result.data_array or []
    return MetricsOut(
        customer_id=customer_id,
        lifetime_spend=float(lifetime or 0),
        last_30d_spend=float(l30 or 0),
        last_90d_spend=float(l90 or 0),
        open_tickets=int(open_t or 0),
        avg_csat=float(csat) if csat is not None else None,
        top_categories=[CategorySpend(category=c[0], spend=float(c[1])) for c in cat_rows],
    )


# ── notes + segment override (transactional staging writes + audit) ──────────
@router.get("/{customer_id}/notes", response_model=list[NoteOut], operation_id="listNotes")
async def list_notes(customer_id: str):
    async with lakebase_sp() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT note_id::text, customer_id, author_email, note_text, created_at, "
                "processed FROM customer_notes_staging WHERE customer_id = %s "
                "ORDER BY created_at DESC",
                (customer_id,),
            )
            return [NoteOut(**r) for r in await cur.fetchall()]


@router.post("/{customer_id}/notes", response_model=NoteOut, operation_id="createNote")
async def create_note(customer_id: str, body: NoteIn, request: Request):
    actor = actor_email(request)
    async with lakebase_sp() as conn:
        async with conn.transaction():
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "INSERT INTO customer_notes_staging (customer_id, author_email, note_text) "
                    "VALUES (%s, %s, %s) RETURNING note_id::text, customer_id, author_email, "
                    "note_text, created_at, processed",
                    (customer_id, actor, body.note_text),
                )
                note = await cur.fetchone()
                await cur.execute(
                    "INSERT INTO customer_audit_log (customer_id, action, actor_email, payload) "
                    "VALUES (%s, %s, %s, %s)",
                    (customer_id, "add_note", actor,
                     json.dumps({"note_id": note["note_id"]})),
                )
    return NoteOut(**note)


@router.get("/{customer_id}/segment", response_model=SegmentOverrideOut | None,
            operation_id="getSegmentOverride")
async def get_segment_override(customer_id: str):
    async with lakebase_sp() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT customer_id, override_segment, reason, author_email, created_at "
                "FROM customer_segment_overrides_staging WHERE customer_id = %s",
                (customer_id,),
            )
            row = await cur.fetchone()
    return SegmentOverrideOut(**row) if row else None


@router.post("/{customer_id}/segment", response_model=SegmentOverrideOut,
             operation_id="overrideSegment")
async def override_segment(customer_id: str, body: SegmentOverrideIn, request: Request):
    actor = actor_email(request)
    async with lakebase_sp() as conn:
        async with conn.transaction():
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "INSERT INTO customer_segment_overrides_staging "
                    "(customer_id, override_segment, reason, author_email) "
                    "VALUES (%s, %s, %s, %s) "
                    "ON CONFLICT (customer_id) DO UPDATE SET "
                    "override_segment = EXCLUDED.override_segment, "
                    "reason = EXCLUDED.reason, author_email = EXCLUDED.author_email, "
                    "created_at = NOW(), processed = FALSE "
                    "RETURNING customer_id, override_segment, reason, author_email, created_at",
                    (customer_id, body.override_segment, body.reason, actor),
                )
                row = await cur.fetchone()
                await cur.execute(
                    "INSERT INTO customer_audit_log (customer_id, action, actor_email, payload) "
                    "VALUES (%s, %s, %s, %s)",
                    (customer_id, "override_segment", actor,
                     json.dumps({"segment": body.override_segment})),
                )
    return SegmentOverrideOut(**row)
