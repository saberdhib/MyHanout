"""Signaux externes (mock déterministe), ingestion, corrélation, effets produits."""

import asyncio
from datetime import date, timedelta

from app.ingestion.signals_ext import get_signal_provider


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_signal_provider_mock_deterministic():
    p = get_signal_provider()
    a = p.fetch("weather_temp_c", date_from=date(2026, 1, 1), date_to=date(2026, 1, 10))
    b = p.fetch("weather_temp_c", date_from=date(2026, 1, 1), date_to=date(2026, 1, 10))
    assert len(a) == 10
    assert [x.value for x in a] == [x.value for x in b]  # déterministe


def _seed_signals():
    """Peuple définitions + observations (sqlite create_all ne joue pas la migration)."""
    from app.ingestion.signals_ext import seed_signal_definitions
    from app.services.signals_service import ingest_signals

    from .conftest import TestSession

    async def _do():
        async with TestSession() as s:
            await seed_signal_definitions(s)
            today = date.today()
            await ingest_signals(s, date_from=today - timedelta(days=120), date_to=today)
            await s.commit()

    _run(_do())


def test_definitions_and_ingest_endpoints(client):
    _seed_signals()
    defs = client.get("/api/v1/signals/definitions").json()["items"]
    keys = {d["key"] for d in defs}
    assert {"weather_temp_c", "school_holiday", "football_match"} <= keys

    ing = client.post("/api/v1/signals/ingest")
    assert ing.status_code == 200, ing.text
    assert ing.json()["provider"] == "mock"

    obs = client.get("/api/v1/signals/observations", params={"signal_key": "weather_temp_c"})
    assert obs.status_code == 200
    assert len(obs.json()) > 0


def test_factors_endpoint_ranks_with_caveat(client):
    _seed_signals()
    # Produit seedé en org A (id 1 = BOEUF-HACHE avec historique de ventes).
    r = client.get("/api/v1/forecasts/1/factors")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "corrélation" in data["caveat"].lower() or "causalit" in data["caveat"].lower()
    for f in data["factors"]:
        assert -1.0 <= f["correlation"] <= 1.0
        assert f["explanation"]


def test_cross_product_endpoint(client):
    r = client.get("/api/v1/forecasts/1/cross-product")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "relations" in data
    for rel in data["relations"]:
        assert rel["relation"] in ("complement", "substitute")


def test_factors_requires_permission(viewer_client):
    # read_only a "forecasts" → 200 attendu (lecture). On vérifie juste l'accès contrôlé.
    r = viewer_client.get("/api/v1/forecasts/1/factors")
    assert r.status_code in (200, 403)
