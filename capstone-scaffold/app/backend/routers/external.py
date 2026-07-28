"""External partner API (T3a) — M2M only.

Partners authenticate as a service principal (client_credentials → OAuth
bearer). The Apps proxy validates and forwards ``X-Forwarded-Access-Token``;
this handler reads **gold via the SQL warehouse using that caller bearer
(OBO)** — never Lakebase, never the app SP — so warehouse audit attributes the
statement to the calling SP.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from backend.auth import obo_client
from backend.models import CustomerDetailOut, TransactionOut
from backend.settings import settings

log = logging.getLogger("customer360.external")
router = APIRouter(prefix="/api/external", tags=["external"])


@router.get("/customers/{customer_id}", response_model=CustomerDetailOut,
            operation_id="externalGetCustomer")
def external_get_customer(customer_id: str, request: Request):
    from databricks.sdk.service.sql import StatementParameterListItem

    w = obo_client(request)  # 401 if no bearer; no SP fallback by design
    gold = settings.gold
    params = [StatementParameterListItem(name="cid", value=customer_id)]

    def run(sql: str):
        return w.statement_execution.execute_statement(
            warehouse_id=settings.warehouse_id, statement=sql,
            parameters=params, wait_timeout="30s",
        )

    cust = run(
        f"SELECT customer_id, first_name, last_name, email, phone, country, city, age, "
        f"gender, signup_date, last_purchase_date, segment_id, lifetime_value, churn_score "
        f"FROM {gold}.customers WHERE customer_id = :cid"
    )
    rows = cust.result.data_array or []
    if not rows:
        raise HTTPException(404, "customer not found")
    c = rows[0]

    txns = run(
        f"SELECT transaction_id, product_id, CAST(transaction_date AS STRING), channel, status, "
        f"amount FROM {gold}.transactions WHERE customer_id = :cid "
        f"ORDER BY transaction_date DESC LIMIT 20"
    )
    trows = txns.result.data_array or []

    return CustomerDetailOut(
        customer_id=c[0], first_name=c[1], last_name=c[2], email=c[3], phone=c[4],
        country=c[5], city=c[6], age=int(c[7]) if c[7] is not None else None, gender=c[8],
        signup_date=c[9], last_purchase_date=c[10], segment_id=c[11],
        lifetime_value=float(c[12]), churn_score=float(c[13]),
        recent_transactions=[
            TransactionOut(
                transaction_id=t[0], product_id=t[1], transaction_date=t[2],
                channel=t[3], status=t[4], amount=float(t[5]) if t[5] is not None else None,
            ) for t in trows
        ],
    )
