"""Smoke test du service ML isolé (keyless, autonome).

On appelle les handlers directement (pas de `TestClient`) : le service n'a
besoin ni de httpx ni de réseau pour être testé.
"""

from app import PredictRequest, health, model_version, predict


def test_health_and_version():
    assert health()["status"] == "ok"
    assert "model_version" in model_version()


def test_predict_returns_horizon_points():
    history = [{"ds": f"2026-05-{d:02d}", "y": 10 + d} for d in range(1, 20)]
    result = predict(PredictRequest(product_id=1, horizon_days=7, model="naive", history=history))
    assert len(result.points) == 7
    assert all(p.yhat >= 0 for p in result.points)
    assert result.explanation


def test_predict_empty_history():
    result = predict(PredictRequest(horizon_days=5, history=[]))
    assert result.points == []
