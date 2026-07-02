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


class BacktestModelOut(BaseModel):
    model: str
    available: bool
    mae: float | None = None
    mape: float | None = None
    n_points: int = 0
    note: str | None = None


class BacktestOut(BaseModel):
    product_id: int | None = None
    horizon_days: int
    folds: int
    history_points: int
    results: list[BacktestModelOut] = []
    best_model: str | None = None
    verdict: str
