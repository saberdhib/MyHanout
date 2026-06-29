"""Forecasting : sélection du modèle configuré + types publics."""

from app.config import settings
from app.intelligence.forecasting.base import (
    ForecastModel,
    ForecastPoint,
    ForecastResult,
    HistoryPoint,
)


def get_forecast_model(name: str | None = None) -> ForecastModel:
    """Retourne le modèle de forecasting configuré (cf. FORECAST_MODEL)."""
    model = (name or settings.forecast_model).lower()
    if model == "prophet":
        from app.intelligence.forecasting.prophet_model import ProphetForecastModel

        return ProphetForecastModel()
    if model == "lgbm":
        from app.intelligence.forecasting.lgbm_model import LightGBMForecastModel

        return LightGBMForecastModel()
    from app.intelligence.forecasting.naive_model import NaiveForecastModel

    return NaiveForecastModel()


__all__ = [
    "ForecastModel",
    "ForecastPoint",
    "ForecastResult",
    "HistoryPoint",
    "get_forecast_model",
]
