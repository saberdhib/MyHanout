"""Schémas du tableau d'impact (ROI)."""

from __future__ import annotations

from pydantic import BaseModel


class ImpactLine(BaseModel):
    label: str
    amount: float
    unit: str  # € | h
    kind: str  # gain | detected | revenue | time
    explanation: str


class ImpactView(BaseModel):
    period_days: int
    currency: str = "EUR"
    estimated_value_eur: float
    time_saved_hours: float
    revenue: float
    lines: list[ImpactLine] = []
    explanation: str
    disclaimer: str
