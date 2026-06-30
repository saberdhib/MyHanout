"""Tests du briefing du matin : consolidation, tâches, envoi, pipeline, isolation."""

from __future__ import annotations

import asyncio
import datetime
import uuid
from datetime import date, timedelta

from sqlalchemy import select

import app.models as m
from app.core.tenancy import tenant_context
from tests.conftest import TestSession, _login


async def _seed_briefing_data(slug: str = "org-a") -> int:
    """Crée un lot frais à risque (démarque) + un produit fini avec recette (production)."""
    async with TestSession() as s:
        org = (await s.scalars(select(m.Organization).where(m.Organization.slug == slug))).first()
        assert org is not None
        suffix = uuid.uuid4().hex[:8]
        with tenant_context(org.id):
            # Démarque : périssable surdimensionné proche péremption.
            yog = m.Product(
                sku=f"YOG-{suffix}",
                name="Yaourt brief",
                unit="unit",
                unit_price=10,
                perishable=True,
            )
            # Production : produit fini + ingrédient + ventes.
            pain = m.Product(
                sku=f"PAIN-{suffix}",
                name="Pain brief",
                unit="unit",
                unit_price=2.5,
                perishable=True,
            )
            farine = m.Product(sku=f"FAR-{suffix}", name="Farine brief", unit="kg", unit_price=8.5)
            s.add_all([yog, pain, farine])
            await s.flush()
            s.add(
                m.Stock(
                    product_id=yog.id,
                    quantity=15,
                    reorder_threshold=10,
                    expiry_date=date.today() + timedelta(days=1),
                )
            )
            s.add(m.Stock(product_id=pain.id, quantity=5, reorder_threshold=20))
            base = datetime.datetime(2026, 5, 1)
            for d in range(20):
                s.add(
                    m.Sale(
                        product_id=yog.id,
                        quantity=2,
                        unit_price=10,
                        total=20,
                        sold_at=base + timedelta(days=d),
                    )
                )
                s.add(
                    m.Sale(
                        product_id=pain.id,
                        quantity=8,
                        unit_price=2.5,
                        total=20,
                        sold_at=base + timedelta(days=d),
                    )
                )
            recipe = m.Recipe(product_id=pain.id, name="Pain (fournée)", yield_quantity=20)
            recipe.items.append(
                m.RecipeItem(ingredient_product_id=farine.id, quantity=10, unit="kg")
            )
            s.add(recipe)
            await s.flush()  # flush DANS le tenant_context → estampille organization_id
        await s.commit()
        return org.id


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_generate_consolidates_agents(client):
    _run(_seed_briefing_data())
    r = client.post("/api/v1/briefing/generate")
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["total_items"] > 0
    assert b["summary"]
    cats = {it["category"] for it in b["items"]}
    # La démarque et la production doivent apparaître dans le briefing consolidé.
    assert "markdown" in cats
    assert "production" in cats
    # Items triés par priorité croissante.
    prios = [it["priority"] for it in b["items"]]
    assert prios == sorted(prios)


def test_item_done_and_send(client):
    _run(_seed_briefing_data())
    b = client.post("/api/v1/briefing/generate").json()
    first = b["items"][0]
    assert client.post(f"/api/v1/briefing/items/{first['id']}/done").status_code == 204

    sent = client.post(f"/api/v1/briefing/{b['id']}/send")
    assert sent.status_code == 200
    assert sent.json()["status"] == "sent"


def test_daily_pipeline_produces_briefing(client):
    _run(_seed_briefing_data())
    client.post("/api/v1/pipelines/daily/trigger")
    b = client.get("/api/v1/briefing").json()
    assert b is not None
    assert b["summary"]


def test_briefing_isolated_between_tenants(anon_client):
    _run(_seed_briefing_data("org-a"))
    a_token = _login(anon_client, "admin@test.local")
    anon_client.headers["Authorization"] = f"Bearer {a_token}"
    a = anon_client.post("/api/v1/briefing/generate").json()
    assert a["id"]

    b_token = _login(anon_client, "owner@b.local")
    anon_client.headers["Authorization"] = f"Bearer {b_token}"
    # B n'a jamais généré : son dernier briefing n'est pas celui de A.
    b_latest = anon_client.get("/api/v1/briefing").json()
    assert b_latest is None or b_latest["id"] != a["id"]
