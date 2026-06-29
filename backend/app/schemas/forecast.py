"""Schémas forecast (réexpose les types du module forecasting)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class ForecastPointOut(BaseModel):
    ds: date
    yhat: float
    yhat_lower: float | None = None
    yhat_upper: float | None = None


class ForecastOut(BaseModel):
    product_id: int | None = None
    model: str
    horizon_days: int
    points: list[ForecastPointOut] = []
    explanation: str | None = None
