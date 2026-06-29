"""Import JSON générique + synchronisation DWH (mock keyless), tenant-scopé."""

_PAYLOAD = {
    "suppliers": [{"name": "Primeur Test", "lead_time_days": 2}],
    "products": [
        {
            "sku": "carotte",
            "name": "Carotte botte",
            "unit": "botte",
            "unit_price": 1.5,
            "perishable": True,
            "supplier_name": "Primeur Test",
            "stock_quantity": 30,
            "reorder_threshold": 12,
        }
    ],
    "sales": [
        {"sku": "carotte", "quantity": 4, "unit_price": 1.5, "sold_at": "2026-06-27T09:00:00Z"}
    ],
}


def test_import_json_upserts_and_is_idempotent(client):
    r1 = client.post("/api/v1/import/json", json=_PAYLOAD)
    assert r1.status_code == 200, r1.text
    data = r1.json()
    assert data["products_upserted"] == 1
    assert data["stocks_upserted"] == 1
    assert data["sales_inserted"] == 1

    # Le produit est visible via l'API stocks (tenant courant).
    stocks = client.get("/api/v1/stocks").json()["items"]
    assert any(s["product_sku"] == "CAROTTE" for s in stocks)

    # Ré-import : le produit/stock sont mis à jour (pas dupliqués).
    r2 = client.post("/api/v1/import/json", json=_PAYLOAD)
    assert r2.json()["products_upserted"] == 1
    skus = [s["product_sku"] for s in client.get("/api/v1/stocks").json()["items"]]
    assert skus.count("CAROTTE") == 1


def test_dwh_sync_mock(client):
    resp = client.post("/api/v1/import/dwh/sync")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["target"] == "mock"
    assert data["rows"] >= 0


def test_import_requires_auth(anon_client):
    assert anon_client.post("/api/v1/import/json", json={}).status_code in (401, 403)
