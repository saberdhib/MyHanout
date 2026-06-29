"""Couche financière : classifieur, trésorerie, valorisation, marges, alertes, isolation."""

import asyncio

from app.intelligence.finance import get_expense_classifier


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- Classifieur (déterministe, keyless) -----------------------------------
def test_classifier_mock_is_deterministic_and_explained():
    clf = get_expense_classifier()
    a = _run(clf.classify(supplier_name="Orange Pro", label="forfait mobile", total=49.9))
    b = _run(clf.classify(supplier_name="Orange Pro", label="forfait mobile", total=49.9))
    assert a.category_code == b.category_code == "TELECOM"
    assert a.kind.value == "opex"
    assert a.explanation  # explication non vide (obligatoire)


def test_classifier_equipment_is_capex():
    clf = get_expense_classifier()
    r = _run(clf.classify(supplier_name="FroidPro", label="vitrine réfrigérée", total=1290))
    assert r.category_code == "EQUIPMENT"
    assert r.kind.value == "capex"


def test_classifier_default_merchandise_low_confidence():
    clf = get_expense_classifier()
    r = _run(clf.classify(supplier_name="Boucherie X", label="viande", total=300))
    assert r.category_code == "MERCHANDISE"
    assert r.confidence < 0.6


# --- Endpoints finance (org A = owner) --------------------------------------
def test_treasury_endpoint(client):
    r = client.get("/api/v1/finance/treasury")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "estimated_balance" in data
    assert data["disclaimer"]  # mention pré-compta
    assert all(line["explanation"] for line in data["lines"])


def test_inventory_value_endpoint(client):
    r = client.get("/api/v1/finance/inventory-value")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total_value"] >= 0
    assert "at_risk_value" in data
    assert data["explanation"]


def test_margins_endpoint_has_explanation(client):
    r = client.get("/api/v1/finance/margins")
    assert r.status_code == 200, r.text
    data = r.json()
    for item in data["items"]:
        assert item["explanation"]


def test_classify_then_confirm_humanloop(client):
    # Catégories nécessaires côté sqlite (créées via create_all, pas la migration).
    _seed_categories()
    invoices = client.get("/api/v1/finance/expenses").json()["items"]
    assert invoices, "au moins une facture"
    inv_id = invoices[0]["id"]

    # Suggestion IA → source=ai + explication obligatoire.
    s = client.post(f"/api/v1/finance/invoices/{inv_id}/classify")
    assert s.status_code == 200, s.text
    sug = s.json()
    assert sug["classification_source"] == "ai"
    assert sug["classification_explanation"]

    # Validation humaine → source=human.
    cats = client.get("/api/v1/finance/categories").json()["items"]
    equipment = next(c for c in cats if c["code"] == "EQUIPMENT")
    c = client.post(
        f"/api/v1/finance/invoices/{inv_id}/classification",
        json={"category_id": equipment["id"], "kind": "capex"},
    )
    assert c.status_code == 200, c.text
    assert c.json()["classification_source"] == "human"
    assert c.json()["expense_kind"] == "capex"


def test_alerts_endpoint(client):
    r = client.get("/api/v1/finance/alerts")
    assert r.status_code == 200, r.text
    assert "alerts" in r.json()
    assert r.json()["explanation"]


# --- Isolation multi-tenant -------------------------------------------------
def test_finance_isolation_between_tenants(client, org_b_client):
    # Org B ne voit que ses propres factures dans /finance/expenses.
    a_numbers = {i["number"] for i in client.get("/api/v1/finance/expenses").json()["items"]}
    b_numbers = {i["number"] for i in org_b_client.get("/api/v1/finance/expenses").json()["items"]}
    # La facture seedée d'A (FAC-1) ne doit jamais apparaître chez B.
    assert a_numbers & b_numbers == set() or "FAC-1" not in b_numbers


def test_finance_requires_permission(viewer_client):
    # read_only n'a pas le scope finance.
    assert viewer_client.get("/api/v1/finance/treasury").status_code == 403


def _seed_categories():
    """Peuple le référentiel global (sqlite create_all ne joue pas la migration)."""
    from app.intelligence.finance.categories import seed_expense_categories

    from .conftest import TestSession

    async def _do():
        async with TestSession() as s:
            await seed_expense_categories(s)
            await s.commit()

    _run(_do())
