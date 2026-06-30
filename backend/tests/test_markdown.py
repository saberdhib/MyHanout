"""Tests de la démarque anti-gaspillage : moteur pur, API scan/apply, isolation tenant."""

from __future__ import annotations

import asyncio
import datetime
import uuid
from datetime import date, timedelta

from sqlalchemy import select

import app.models as m
from app.core.tenancy import tenant_context
from app.intelligence.markdown.engine import decide_markdown
from app.models.base import PriceKind
from tests.conftest import TestSession, _login


# --- Moteur de démarque : règles pures, explicables -------------------------
def test_markdown_suggested_when_leftover():
    d = decide_markdown(
        product_id=1,
        quantity=15,
        days_to_expiry=2,
        avg_daily_demand=2.0,
        current_price=10.0,
        unit_cost=6.0,
        history_days=30,
    )
    assert d is not None
    assert 0 < d.discount_pct <= 50
    assert d.suggested_price < d.current_price
    assert d.recovered_value >= 0
    assert d.baseline_loss > 0  # sans action, perte réelle
    assert d.explanation and d.reasons  # explicabilité


def test_no_markdown_when_sells_through():
    # Forte demande : tout le lot s'écoule avant péremption → pas de démarque.
    d = decide_markdown(
        product_id=1,
        quantity=4,
        days_to_expiry=3,
        avg_daily_demand=5.0,
        current_price=10.0,
        unit_cost=6.0,
    )
    assert d is None


def test_markdown_picks_smallest_quasi_optimal_tier():
    d = decide_markdown(
        product_id=1,
        quantity=12,
        days_to_expiry=3,
        avg_daily_demand=2.0,
        current_price=10.0,
        unit_cost=6.0,
        tiers=[10, 20, 30, 40, 50],
    )
    assert d is not None
    # palier choisi = plus petit atteignant ~95 % du meilleur cash récupérable.
    assert d.discount_pct in (10, 20, 30, 40, 50)
    assert d.data_used["leftover_full_price"] > 0


# --- Setup données pour l'org A (lot frais à risque) -------------------------
async def _seed_markdown_lot(slug: str = "org-a") -> tuple[int, int]:
    async with TestSession() as s:
        org = (await s.scalars(select(m.Organization).where(m.Organization.slug == slug))).first()
        assert org is not None
        with tenant_context(org.id):
            prod = m.Product(
                sku=f"MKD-{uuid.uuid4().hex[:8]}",
                name=f"Yaourt démarque {slug}",
                unit="unit",
                unit_price=10,
                perishable=True,
            )
            s.add(prod)
            await s.flush()
            base = datetime.datetime(2026, 5, 1)
            for d in range(20):  # ~2 ventes/jour → demande modérée
                s.add(
                    m.Sale(
                        product_id=prod.id,
                        quantity=2,
                        unit_price=10,
                        total=20,
                        sold_at=base + timedelta(days=d),
                    )
                )
            s.add(
                m.Stock(
                    product_id=prod.id,
                    quantity=15,
                    reorder_threshold=10,
                    expiry_date=date.today() + timedelta(days=1),  # lot surdimensionné
                )
            )
            s.add(
                m.PriceHistory(
                    product_id=prod.id,
                    kind=PriceKind.PURCHASE,
                    price=6,
                    effective_at=datetime.datetime(2026, 5, 1, tzinfo=datetime.UTC),
                    source="test",
                )
            )
            await s.flush()  # flush DANS le tenant_context → estampille organization_id
        await s.commit()
        return prod.id, org.id


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- API : scan + appliquer + rejeter ---------------------------------------
def test_scan_and_apply_markdown(client):
    pid, _ = _run(_seed_markdown_lot())
    r = client.post("/api/v1/markdown/scan")
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    mine = next((it for it in items if it["product_id"] == pid), None)
    assert mine is not None, "le lot frais à risque doit générer une démarque"
    assert mine["discount_pct"] > 0
    assert mine["baseline_loss"] > 0
    assert mine["status"] == "suggested"
    assert mine["explanation"]

    applied = client.post(f"/api/v1/markdown/{mine['id']}/apply")
    assert applied.status_code == 200, applied.text
    assert applied.json()["status"] == "applied"

    # La liste filtrée "applied" contient bien notre démarque.
    done = client.get("/api/v1/markdown", params={"status": "applied"}).json()["items"]
    assert any(it["id"] == mine["id"] for it in done)


def test_reject_markdown(client):
    pid, _ = _run(_seed_markdown_lot())
    client.post("/api/v1/markdown/scan")
    suggested = client.get("/api/v1/markdown", params={"status": "suggested"}).json()["items"]
    target = next((it for it in suggested if it["product_id"] == pid), None)
    assert target is not None
    r = client.post(f"/api/v1/markdown/{target['id']}/reject")
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


# --- Isolation tenant -------------------------------------------------------
def test_markdown_isolated_between_tenants(anon_client):
    a_pid, _ = _run(_seed_markdown_lot("org-a"))
    a_token = _login(anon_client, "admin@test.local")
    anon_client.headers["Authorization"] = f"Bearer {a_token}"
    anon_client.post("/api/v1/markdown/scan")
    a_items = anon_client.get("/api/v1/markdown").json()["items"]
    a_ids = {it["id"] for it in a_items}
    assert a_ids  # A a des démarques

    b_token = _login(anon_client, "owner@b.local")
    anon_client.headers["Authorization"] = f"Bearer {b_token}"
    b_items = anon_client.get("/api/v1/markdown").json()["items"]
    b_ids = {it["id"] for it in b_items}
    # B ne voit AUCUNE démarque de A.
    assert a_ids.isdisjoint(b_ids)
