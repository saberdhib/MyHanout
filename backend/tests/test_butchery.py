"""Boucherie (lots/coupes, rendement, traçabilité), familles produit, historique prix."""


def test_config_modules(client):
    r = client.get("/api/v1/config/modules")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "enabled" in data and isinstance(data["enabled"], list)
    # Le socle minimal est toujours présent.
    assert {"dashboard", "stocks", "finance"} <= set(data["enabled"])


def test_families_endpoint(client):
    r = client.get("/api/v1/catalog/families")
    assert r.status_code == 200, r.text
    fams = r.json()
    assert "viande" in fams and "boisson" in fams


def test_meat_lot_breakdown_yield_and_cost(client):
    # 1) Crée une bête : demi-bœuf 150 kg à 1200 €.
    lot = client.post(
        "/api/v1/meat/lots",
        json={
            "lot_code": "BOV-2026-001",
            "species": "boeuf",
            "label": "demi-bœuf",
            "gross_weight_kg": 150,
            "purchase_cost": 1200,
        },
    )
    assert lot.status_code == 200, lot.text
    lot_id = lot.json()["id"]

    # 2) Décompose : 100 kg valorisables + 30 kg os/perte (réel saisi).
    bd = client.put(
        f"/api/v1/meat/lots/{lot_id}/breakdown",
        json={
            "cuts": [
                {"cut_label": "aloyau", "actual_weight_kg": 40},
                {"cut_label": "épaule", "actual_weight_kg": 60},
                {"cut_label": "os", "actual_weight_kg": 30, "is_waste": True},
            ]
        },
    )
    assert bd.status_code == 200, bd.text
    s = bd.json()
    assert s["saleable_weight_kg"] == 100.0
    assert s["waste_weight_kg"] == 30.0
    # rendement = 100/150 ≈ 0.6667
    assert abs(s["yield_pct"] - (100 / 150)) < 1e-3
    # coût/kg valorisable = 1200/100 = 12.0
    assert s["cost_per_kg"] == 12.0
    # allocation : aloyau 40kg → 480 €
    aloyau = next(c for c in s["cuts"] if c["cut_label"] == "aloyau")
    assert aloyau["allocated_cost"] == 480.0
    # l'os ne reçoit pas de coût (perte)
    os_cut = next(c for c in s["cuts"] if c["cut_label"] == "os")
    assert os_cut["allocated_cost"] is None
    assert s["traceability"].startswith("Lot BOV-2026-001")
    assert s["status"] == "done"


def test_meat_isolation(anon_client):
    # client/org_b_client partagent le TestClient → on pilote le token explicitement.
    from .conftest import _login

    anon_client.headers["Authorization"] = f"Bearer {_login(anon_client, 'admin@test.local')}"
    anon_client.post(
        "/api/v1/meat/lots",
        json={
            "lot_code": "ISO-A-LOT",
            "species": "boeuf",
            "label": "demi-bœuf",
            "gross_weight_kg": 100,
            "purchase_cost": 800,
        },
    )
    anon_client.headers["Authorization"] = f"Bearer {_login(anon_client, 'owner@b.local')}"
    b_codes = {row["lot_code"] for row in anon_client.get("/api/v1/meat/lots").json()}
    assert "ISO-A-LOT" not in b_codes


def test_price_history_record_and_list(client):
    # Récupère un produit existant (seedé en org A).
    stocks = client.get("/api/v1/stocks").json()["items"]
    assert stocks
    pid = stocks[0]["product_id"]
    client.post(f"/api/v1/catalog/products/{pid}/prices", json={"kind": "sale", "price": 9.5})
    client.post(f"/api/v1/catalog/products/{pid}/prices", json={"kind": "sale", "price": 10.0})
    hist = client.get(f"/api/v1/catalog/products/{pid}/prices?kind=sale").json()
    assert len(hist) >= 2
    assert hist[-1]["price"] == 10.0
