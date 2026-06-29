"""Tests rate limiting (fenêtre glissante) + tracing (corrélation requêtes)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.rate_limit import RateLimitMiddleware, _SlidingWindow
from app.core.tracing import TracingMiddleware, _trace_id_from_header


def test_sliding_window_allows_then_blocks():
    w = _SlidingWindow(limit=2)
    assert w.allow("k", 1000.0) is True
    assert w.allow("k", 1000.1) is True
    assert w.allow("k", 1000.2) is False  # 3e dans la fenêtre -> bloqué
    # Après 60 s, la fenêtre a glissé -> de nouveau autorisé.
    assert w.allow("k", 1061.0) is True


def test_sliding_window_per_key():
    w = _SlidingWindow(limit=1)
    assert w.allow("a", 1.0) is True
    assert w.allow("b", 1.0) is True  # clé différente, indépendante
    assert w.allow("a", 1.1) is False


def _mini_app(middleware, **kw):
    app = FastAPI()
    app.add_middleware(middleware, **kw)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    return app


def test_rate_limit_middleware_returns_429(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    client = TestClient(_mini_app(RateLimitMiddleware, limit=2))
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    r = client.get("/ping")
    assert r.status_code == 429
    assert r.headers.get("Retry-After") == "60"


def test_tracing_sets_request_id_header():
    client = TestClient(_mini_app(TracingMiddleware))
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID")


@pytest.mark.parametrize(
    "header,expected_len",
    [("00-" + "a" * 32 + "-" + "b" * 16 + "-01", 32), (None, 0), ("bad", 0)],
)
def test_trace_id_parsing(header, expected_len):
    out = _trace_id_from_header(header)
    assert (len(out) if out else 0) == expected_len
