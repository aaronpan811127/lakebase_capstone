"""Tests for config, external (401 guard), genie (401 guard), jobs (503 guard)."""
from fastapi.testclient import TestClient

from backend.main import app
from backend.routers import config as config_router

client = TestClient(app)


def test_config_returns_ids(monkeypatch):
    monkeypatch.setattr(config_router.settings, "databricks_host", "https://ws.example.com/")
    monkeypatch.setattr(config_router.settings, "dashboard_id", "dash123")
    monkeypatch.setattr(config_router.settings, "genie_space_id", "genie456")
    config_router._config_cache.clear()
    r = client.get("/api/config")
    assert r.status_code == 200
    body = r.json()
    assert body["dashboard_id"] == "dash123"
    assert body["databricks_host"] == "https://ws.example.com"  # trailing slash stripped


def test_me_reads_forwarded_email():
    r = client.get("/api/me", headers={"X-Forwarded-Email": "rep@acme.com"})
    assert r.json()["email"] == "rep@acme.com"


def test_external_requires_obo():
    r = client.get("/api/external/customers/C0000001")
    assert r.status_code == 401


def test_genie_start_requires_obo():
    r = client.post("/api/genie/conversations", json={"content": "hi"})
    assert r.status_code == 401


def test_run_forward_etl_503_without_job(monkeypatch):
    from backend.routers import jobs as jobs_router
    monkeypatch.setattr(jobs_router.settings, "forward_etl_job_id", "")
    r = client.post("/api/jobs/run-forward-etl")
    assert r.status_code == 503
