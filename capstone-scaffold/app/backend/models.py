"""Pydantic request/response models (3-model pattern: In / Out / ListOut)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25


# ── customers ───────────────────────────────────────────────────────────────
class CustomerListItem(BaseModel):
    customer_id: str
    first_name: str
    last_name: str
    email: str
    country: str
    segment_id: str
    lifetime_value: float
    churn_score: float


class CustomerListOut(BaseModel):
    items: list[CustomerListItem]
    total: int
    page: int
    page_size: int


class TransactionOut(BaseModel):
    transaction_id: str
    product_id: str
    transaction_date: date | None = None
    channel: str | None = None
    status: str | None = None
    amount: float | None = None


class CustomerDetailOut(BaseModel):
    customer_id: str
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    country: str | None = None
    city: str | None = None
    age: int | None = None
    gender: str | None = None
    signup_date: date | None = None
    last_purchase_date: date | None = None
    segment_id: str
    lifetime_value: float
    churn_score: float
    recent_transactions: list[TransactionOut] = Field(default_factory=list)


class CategorySpend(BaseModel):
    category: str
    spend: float


class MetricsOut(BaseModel):
    customer_id: str
    lifetime_spend: float
    top_categories: list[CategorySpend]
    last_30d_spend: float
    last_90d_spend: float
    open_tickets: int
    avg_csat: float | None = None


# ── notes ───────────────────────────────────────────────────────────────────
class NoteIn(BaseModel):
    note_text: str = Field(min_length=1, max_length=5000)


class NoteOut(BaseModel):
    note_id: str
    customer_id: str
    author_email: str
    note_text: str
    created_at: datetime
    processed: bool


# ── segment override ─────────────────────────────────────────────────────────
class SegmentOverrideIn(BaseModel):
    override_segment: str = Field(min_length=1, max_length=10)
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("override_segment")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.strip().upper()


class SegmentOverrideOut(BaseModel):
    customer_id: str
    override_segment: str
    reason: str | None = None
    author_email: str
    created_at: datetime


# ── config / jobs ────────────────────────────────────────────────────────────
class ConfigOut(BaseModel):
    databricks_host: str
    dashboard_id: str
    genie_space_id: str


class MeOut(BaseModel):
    email: str
    workspace_host: str


class RunOut(BaseModel):
    run_id: int
    state: str
    result_state: str | None = None
    run_page_url: str | None = None
    start_time: int | None = None
    end_time: int | None = None
