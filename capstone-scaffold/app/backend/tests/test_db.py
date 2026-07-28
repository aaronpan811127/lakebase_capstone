from backend import db


def test_conninfo_from_settings(monkeypatch):
    monkeypatch.setattr(db, "_pg_user", lambda: "sp-client-id")
    monkeypatch.setattr(db.settings, "pghost", "pg.example.com")
    monkeypatch.setattr(db.settings, "pgdatabase", "capstone_db")
    ci = db._conninfo()
    assert "host=pg.example.com" in ci
    assert "dbname=capstone_db" in ci
    assert "user=sp-client-id" in ci
    assert "sslmode=require" in ci


def test_build_pool_does_not_open(monkeypatch):
    monkeypatch.setattr(db, "_pg_user", lambda: "sp-client-id")
    pool = db.build_pool()
    # open=False means no connection attempt at construction time
    assert pool.closed is True
    assert pool.connection_class is db._TokenAuthConnection
