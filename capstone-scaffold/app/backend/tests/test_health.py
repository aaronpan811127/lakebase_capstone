from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_request_id_header():
    r = client.get("/api/health")
    assert r.headers.get("X-Request-Id")


def test_request_id_echoed_when_supplied():
    r = client.get("/api/health", headers={"X-Request-Id": "abc-123"})
    assert r.headers.get("X-Request-Id") == "abc-123"
