"""Tests saisie fin de journée + boucle MLOps (écart prévu/réel)."""


def test_create_daily_entry(client):
    resp = client.post(
        "/api/v1/daily-entries",
        json={
            "product_id": 1,
            "entry_date": "2026-06-10",
            "quantity_ordered": 12,
            "stock_remaining": 3,
            "source": "dashboard",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["quantity_ordered"] == 12


def test_daily_entry_idempotent(client):
    base = {
        "product_id": 1,
        "entry_date": "2026-06-11",
        "quantity_ordered": 5,
        "stock_remaining": 2,
    }
    r1 = client.post("/api/v1/daily-entries", json=base)
    r2 = client.post("/api/v1/daily-entries", json={**base, "quantity_ordered": 9})
    # Même (produit, date) -> même ligne, valeur mise à jour.
    assert r1.json()["id"] == r2.json()["id"]
    assert r2.json()["quantity_ordered"] == 9


def test_mlops_evaluation_and_metrics(client):
    # Deux jours consécutifs -> demande réelle déduite + écart calculé.
    client.post(
        "/api/v1/daily-entries",
        json={
            "product_id": 1,
            "entry_date": "2026-06-12",
            "quantity_ordered": 0,
            "stock_remaining": 20,
        },
    )
    client.post(
        "/api/v1/daily-entries",
        json={
            "product_id": 1,
            "entry_date": "2026-06-13",
            "quantity_ordered": 10,
            "stock_remaining": 5,
        },
    )
    resp = client.get("/api/v1/mlops/metrics", params={"product_id": 1})
    assert resp.status_code == 200
    metrics = resp.json()["metrics"]
    assert metrics, "des métriques d'erreur doivent exister"
    assert metrics[0]["mae"] is not None


def test_mlops_retrain_versions_model(client):
    resp = client.post("/api/v1/mlops/retrain", params={"product_id": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_version"]
    assert data["products_retrained"] >= 1
