"""Tests unitaires du modèle de forecasting naïf."""

from datetime import date

from app.intelligence.forecasting import HistoryPoint, get_forecast_model


def test_naive_forecast_basic():
    history = [HistoryPoint(ds=date(2026, 5, 1), y=10 + i % 3) for i in range(30)]
    model = get_forecast_model("naive")
    result = model.predict(history, horizon_days=14, product_id=1)
    assert result.model == "naive"
    assert len(result.points) == 14
    assert all(p.yhat >= 0 for p in result.points)


def test_naive_forecast_empty_history():
    model = get_forecast_model("naive")
    result = model.predict([], horizon_days=7)
    assert result.points == []
    assert "Aucun historique" in (result.explanation or "")
