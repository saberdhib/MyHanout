"""Smoke test du service ML isolé (keyless, autonome)."""

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_health_and_version():
    assert client.get("/health").json()["status"] == "ok"
    assert "model_version" in client.get("/model/version").json()


def test_predict_returns_horizon_points():
    history = [{"ds": f"2026-05-{d:02d}", "y": 10 + d} for d in range(1, 20)]
    resp = client.post(
        "/predict", json={"product_id": 1, "horizon_days": 7, "model": "naive", "history": history}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["points"]) == 7
    assert all(p["yhat"] >= 0 for p in body["points"])
    assert body["explanation"]


def test_predict_empty_history():
    resp = client.post("/predict", json={"horizon_days": 5, "history": []})
    assert resp.json()["points"] == []
