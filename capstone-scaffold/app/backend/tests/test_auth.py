import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend import auth


def _req(headers: dict) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw})


def test_obo_missing_token_401(monkeypatch):
    monkeypatch.setattr(auth, "WorkspaceClient", lambda **kw: object())
    with pytest.raises(HTTPException) as ei:
        auth.obo_client(_req({}))
    assert ei.value.status_code == 401


def test_obo_reads_token(monkeypatch):
    seen = {}

    def fake_ws(**kw):
        seen.update(kw)
        return object()

    monkeypatch.setattr(auth, "WorkspaceClient", fake_ws)
    auth.obo_client(_req({"X-Forwarded-Access-Token": "tok-42"}))
    assert seen.get("token") == "tok-42"
    assert seen.get("host")  # host wired from settings


def test_actor_email_from_header():
    assert auth.actor_email(_req({"X-Forwarded-Email": "rep@acme.com"})) == "rep@acme.com"


def test_actor_email_fallback():
    assert auth.actor_email(_req({})) == "unknown"
