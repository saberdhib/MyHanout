"""Tests production en magasin : moteur pur, recettes CRUD, plan + isolation tenant."""

from __future__ import annotations

import asyncio
import datetime
import uuid
from datetime import timedelta

from sqlalchemy import select

import app.models as m
from app.core.tenancy import tenant_context
from app.intelligence.production.engine import plan_production
from tests.conftest import TestSession, _login


# --- Moteur de production : règles pures, explicables -----------------------
def test_plan_rounds_up_to_yield():
    d = plan_production(
        product_id=1,
        forecast_demand=112,
        current_stock=10,
        yield_quantity=20,
        horizon_days=14,
        history_days=25,
    )
    assert d.batches == 6  # ceil((112-10)/20)
    assert d.suggested_quantity == 120
    assert d.net_need == 102
    assert d.explanation and d.reasons


def test_plan_no_production_when_stock_covers():
    d = plan_production(
        product_id=1,
        forecast_demand=10,
        current_stock=50,
        yield_quantity=20,
        horizon_days=14,
    )
    assert d.batches == 0
    assert d.suggested_quantity == 0


# --- Setup : un produit fini + recette + ventes pour l'org A ----------------
async def _seed_recipe(slug: str = "org-a") -> tuple[int, int, int]:
    async with TestSession() as s:
        org = (await s.scalars(select(m.Organization).where(m.Organization.slug == slug))).first()
        assert org is not None
        with tenant_context(org.id):
            suffix = uuid.uuid4().hex[:8]
            pain = m.Product(
                sku=f"PAIN-{suffix}",
                name="Pain test",
                unit="unit",
                unit_price=2.5,
                perishable=True,
            )
            farine = m.Product(sku=f"FAR-{suffix}", name="Farine test", unit="kg", unit_price=8.5)
            s.add_all([pain, farine])
            await s.flush()
            s.add(m.Stock(product_id=pain.id, quantity=5, reorder_threshold=20))
            base = datetime.datetime(2026, 5, 1)
            for d in range(20):
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
        return pain.id, farine.id, org.id


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- API : recettes CRUD ----------------------------------------------------
def test_recipe_crud(client):
    # Crée deux produits via le catalogue (fini + ingrédient).
    suffix = uuid.uuid4().hex[:8]
    fin = client.post(
        "/api/v1/catalog/products",
        json={"sku": f"FIN-{suffix}", "name": "Gâteau", "unit": "unit", "unit_price": 5},
    ).json()
    ing = client.post(
        "/api/v1/catalog/products",
        json={"sku": f"ING-{suffix}", "name": "Sucre", "unit": "kg", "unit_price": 9},
    ).json()
    r = client.post(
        "/api/v1/recipes",
        json={
            "product_id": fin["id"],
            "name": "Gâteau (fournée)",
            "yield_quantity": 10,
            "items": [{"ingredient_product_id": ing["id"], "quantity": 2, "unit": "kg"}],
        },
    )
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["items"][0]["ingredient_product_id"] == ing["id"]

    listed = client.get("/api/v1/recipes").json()["items"]
    assert any(rec["id"] == created["id"] for rec in listed)

    assert client.delete(f"/api/v1/recipes/{created['id']}").status_code == 204


# --- API : plan de production + ingrédients ---------------------------------
def test_production_plan_and_ingredients(client):
    pid, fid, _ = _run(_seed_recipe())
    plan = client.get("/api/v1/production/plan").json()
    mine = next((p for p in plan["plans"] if p["product_id"] == pid), None)
    assert mine is not None, "le produit fini avec recette doit apparaître au plan"
    assert mine["suggested_quantity"] > 0
    assert mine["batches"] > 0
    assert mine["explanation"]
    # Le besoin en ingrédient (farine) est agrégé avec un coût estimé.
    need = next((i for i in plan["ingredients"] if i["ingredient_product_id"] == fid), None)
    assert need is not None
    assert need["quantity"] > 0
    assert plan["total_ingredient_cost"] >= 0


def test_production_scan_and_confirm(client):
    pid, _, _ = _run(_seed_recipe())
    scan = client.post("/api/v1/production/scan").json()
    target = next((p for p in scan["plans"] if p["product_id"] == pid), None)
    assert target is not None and target["id"] > 0
    confirmed = client.post(f"/api/v1/production/{target['id']}/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"


# --- Isolation tenant -------------------------------------------------------
def test_recipes_isolated_between_tenants(anon_client):
    _run(_seed_recipe("org-a"))
    a_token = _login(anon_client, "admin@test.local")
    anon_client.headers["Authorization"] = f"Bearer {a_token}"
    a_ids = {r["id"] for r in anon_client.get("/api/v1/recipes").json()["items"]}
    assert a_ids  # A a des recettes

    b_token = _login(anon_client, "owner@b.local")
    anon_client.headers["Authorization"] = f"Bearer {b_token}"
    b_ids = {r["id"] for r in anon_client.get("/api/v1/recipes").json()["items"]}
    assert a_ids.isdisjoint(b_ids)
