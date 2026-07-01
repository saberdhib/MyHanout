"""Tests agents Prix & Effectifs : moteurs purs + endpoints."""

from __future__ import annotations

from app.intelligence.pricing.engine import charm_round, suggest_price
from app.intelligence.staffing.engine import suggest_staff


# --- Moteur Prix ------------------------------------------------------------
def test_pricing_raises_when_margin_below_target():
    d = suggest_price(product_id=1, current_price=8.0, unit_cost=6.0)
    assert d.action == "raise"
    assert d.suggested_price > d.current_price
    assert d.explanation and d.reasons


def test_pricing_never_below_cost():
    d = suggest_price(product_id=1, current_price=5.0, unit_cost=6.0)
    assert d.suggested_price >= 6.0  # jamais sous le coût


def test_charm_rounding():
    assert charm_round(9.13) == 8.99
    assert charm_round(2.41) == 2.49
    assert charm_round(0.75) == 0.75  # < 1 → pas de charm


# --- Moteur Effectifs -------------------------------------------------------
def test_staffing_reinforces_on_peak():
    suggested, delta, vs_avg, expl = suggest_staff(
        predicted_demand=200, average_demand=120, units_per_staff_day=120, base_staff=1
    )
    assert suggested == 2 and delta == 1
    assert vs_avg > 0 and expl


def test_staffing_base_when_quiet():
    suggested, delta, _, _ = suggest_staff(
        predicted_demand=50, average_demand=120, units_per_staff_day=120, base_staff=1
    )
    assert suggested == 1 and delta == 0


# --- API --------------------------------------------------------------------
def test_pricing_suggestions_and_apply(client):
    items = client.get("/api/v1/pricing/suggestions").json()["items"]
    assert isinstance(items, list) and items  # l'org démo a des produits
    pid = items[0]["product_id"]

    applied = client.post("/api/v1/pricing/apply", json={"product_id": pid, "price": 12.34})
    assert applied.status_code == 200, applied.text
    assert applied.json()["current_price"] == 12.34


def test_staffing_plan(client):
    plan = client.get("/api/v1/staffing/plan", params={"horizon_days": 7}).json()
    assert len(plan["days"]) == 7
    assert plan["base_staff"] >= 0
    for d in plan["days"]:
        assert d["suggested_staff"] >= plan["base_staff"]
        assert d["weekday"]
