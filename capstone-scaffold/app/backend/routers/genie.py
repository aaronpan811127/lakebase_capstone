"""Genie conversation endpoints (T5) — all OBO (caller's identity).

Frontend drives a poll loop: start/continue a conversation to get a
message_id, then GET the message until status is terminal; if the answer has
a query attachment, we fetch and inline its result.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel

from backend.auth import obo_client
from backend.settings import settings

log = logging.getLogger("customer360.genie")
router = APIRouter(prefix="/api/genie", tags=["genie"])

_TERMINAL = {"COMPLETED", "FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED"}


class StartIn(BaseModel):
    content: str


class MessageIn(BaseModel):
    content: str


class GenieMessageOut(BaseModel):
    conversation_id: str
    message_id: str
    status: str | None = None
    content: str | None = None
    answer_text: str | None = None
    query: str | None = None
    result_columns: list[str] | None = None
    result_rows: list[list] | None = None


def _status_str(s) -> str | None:
    if s is None:
        return None
    return getattr(s, "value", None) or str(s).split(".")[-1]


def _msg_id(obj) -> str | None:
    return getattr(obj, "message_id", None) or getattr(obj, "id", None)


def _nested_status(resp):
    """start/create responses carry the message under `.message` (GenieMessage)."""
    msg = getattr(resp, "message", None)
    return getattr(msg, "status", None) if msg is not None else getattr(resp, "status", None)


@router.post("/conversations", response_model=GenieMessageOut, operation_id="startGenie")
def start_conversation(body: StartIn, request: Request):
    w = obo_client(request)
    # Wait[GenieMessage].response is the initial GenieStartConversationResponse
    # (ids + nested `.message`); the frontend polls get_message separately.
    resp = w.genie.start_conversation(space_id=settings.genie_space_id, content=body.content).response
    return GenieMessageOut(
        conversation_id=resp.conversation_id,
        message_id=_msg_id(resp),
        status=_status_str(_nested_status(resp)),
    )


@router.post("/conversations/{conversation_id}/messages",
             response_model=GenieMessageOut, operation_id="sendGenieMessage")
def create_message(conversation_id: str, body: MessageIn, request: Request):
    w = obo_client(request)
    resp = w.genie.create_message(
        space_id=settings.genie_space_id, conversation_id=conversation_id, content=body.content
    ).response
    return GenieMessageOut(
        conversation_id=conversation_id,
        message_id=_msg_id(resp),
        status=_status_str(_nested_status(resp)),
    )


@router.get("/conversations/{conversation_id}/messages/{message_id}",
            response_model=GenieMessageOut, operation_id="getGenieMessage")
def get_message(conversation_id: str, message_id: str, request: Request):
    w = obo_client(request)
    msg = w.genie.get_message(
        space_id=settings.genie_space_id, conversation_id=conversation_id, message_id=message_id
    )
    status = _status_str(msg.status)
    out = GenieMessageOut(conversation_id=conversation_id, message_id=message_id, status=status)

    for att in (msg.attachments or []):
        text = getattr(att, "text", None)
        if text and getattr(text, "content", None):
            out.answer_text = text.content
        query = getattr(att, "query", None)
        if query:
            out.query = getattr(query, "query", None)
            if status == "COMPLETED":
                try:
                    res = w.genie.get_message_attachment_query_result(
                        space_id=settings.genie_space_id,
                        conversation_id=conversation_id,
                        message_id=message_id,
                        attachment_id=att.attachment_id,
                    )
                    sr = res.statement_response
                    if sr and sr.manifest and sr.result:
                        out.result_columns = [c.name for c in sr.manifest.schema.columns]
                        out.result_rows = sr.result.data_array or []
                except Exception as e:  # noqa: BLE001
                    log.warning("genie attachment result fetch failed: %s", e)
    out.content = msg.content
    return out
