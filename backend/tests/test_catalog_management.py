"""Tests gestion catalogue : liste/création/édition produits + familles + isolation."""

from __future__ import annotations

from tests.conftest import _login


def test_list_products_and_families(client):
    fams = client.get("/api/v1/catalog/families").json()
    assert "viande" in fams
    products = client.get("/api/v1/catalog/products").json()
    assert products["total"] >= 1
    assert all("family" in p for p in products["items"])


def test_create_then_update_product(client):
    created = client.post(
        "/api/v1/catalog/products",
        json={"sku": "TEST-CAT-1", "name": "Yaourt nature", "family": "cremerie", "unit": "unit"},
    )
    assert created.status_code == 201, created.text
    pid = created.json()["id"]
    assert created.json()["family"] == "cremerie"

    upd = client.patch(
        f"/api/v1/catalog/products/{pid}",
        json={"family": "boisson", "unit_price": 1.2, "perishable": True},
    )
    assert upd.status_code == 200, upd.text
    body = upd.json()
    assert body["family"] == "boisson"
    assert body["unit_price"] == 1.2
    assert body["perishable"] is True


def test_filter_by_family(client):
    client.post(
        "/api/v1/catalog/products",
        json={"sku": "TEST-VIANDE-1", "name": "Steak haché", "family": "viande", "unit": "kg"},
    )
    viande = client.get("/api/v1/catalog/products", params={"family": "viande"}).json()
    assert viande["total"] >= 1
    assert all(p["family"] == "viande" for p in viande["items"])


def test_duplicate_sku_rejected(client):
    client.post("/api/v1/catalog/products", json={"sku": "DUP-1", "name": "A"})
    dup = client.post("/api/v1/catalog/products", json={"sku": "DUP-1", "name": "B"})
    assert dup.status_code == 409


def test_update_missing_product_404(client):
    assert client.patch("/api/v1/catalog/products/999999", json={"name": "x"}).status_code == 404


def test_products_isolated_between_tenants(anon_client):
    # Org A crée un produit ; Org B ne doit pas le voir.
    a = _login(anon_client, "admin@test.local")
    anon_client.headers["Authorization"] = f"Bearer {a}"
    anon_client.post("/api/v1/catalog/products", json={"sku": "ISO-A-ONLY", "name": "Secret A"})
    a_skus = {p["sku"] for p in anon_client.get("/api/v1/catalog/products").json()["items"]}
    assert "ISO-A-ONLY" in a_skus

    b = _login(anon_client, "owner@b.local")
    anon_client.headers["Authorization"] = f"Bearer {b}"
    b_skus = {p["sku"] for p in anon_client.get("/api/v1/catalog/products").json()["items"]}
    assert "ISO-A-ONLY" not in b_skus
