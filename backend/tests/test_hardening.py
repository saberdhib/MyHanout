"""Tests durcissement (Lot 6) : pagination bornée + limite de téléversement."""

from __future__ import annotations

import asyncio

import pytest

from app.core.exceptions import PayloadTooLargeError
from app.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, clamp_limit, clamp_offset


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- Pagination -------------------------------------------------------------


def test_clamp_limit_bounds():
    assert clamp_limit(None) == DEFAULT_PAGE_SIZE
    assert clamp_limit(0) == DEFAULT_PAGE_SIZE
    assert clamp_limit(-5) == DEFAULT_PAGE_SIZE
    assert clamp_limit(10) == 10
    assert clamp_limit(10_000) == MAX_PAGE_SIZE  # plafonné (anti-DoS)


def test_clamp_offset():
    assert clamp_offset(None) == 0
    assert clamp_offset(-3) == 0
    assert clamp_offset(20) == 20


def test_alerts_endpoint_accepts_pagination(client):
    r = client.get("/api/v1/alerts", params={"limit": 1, "offset": 0})
    assert r.status_code == 200
    assert len(r.json()["items"]) <= 1


# --- Limite de téléversement ------------------------------------------------


class _StubUpload:
    def __init__(self, data: bytes, size: int | None) -> None:
        self._data = data
        self.size = size

    async def read(self) -> bytes:
        return self._data


def test_read_bounded_rejects_by_declared_size(monkeypatch):
    from app.core import uploads

    monkeypatch.setattr(uploads.settings, "max_upload_mb", 1)
    big = _StubUpload(b"x", size=2 * 1024 * 1024)  # 2 Mo annoncés > 1 Mo
    with pytest.raises(PayloadTooLargeError):
        _run(uploads.read_bounded(big))


def test_read_bounded_rejects_by_content_when_size_unknown(monkeypatch):
    from app.core import uploads

    monkeypatch.setattr(uploads.settings, "max_upload_mb", 1)
    payload = b"x" * (2 * 1024 * 1024)  # 2 Mo, taille non annoncée
    big = _StubUpload(payload, size=None)
    with pytest.raises(PayloadTooLargeError):
        _run(uploads.read_bounded(big))


def test_read_bounded_accepts_small(monkeypatch):
    from app.core import uploads

    monkeypatch.setattr(uploads.settings, "max_upload_mb", 1)
    ok = _StubUpload(b"hello", size=5)
    assert _run(uploads.read_bounded(ok)) == b"hello"
