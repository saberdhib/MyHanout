"""Schémas Pydantic de l'agent Effectifs (charge de travail prévue → staff)."""

from __future__ import annotations

from pydantic import BaseModel


class StaffingDay(BaseModel):
    date: str
    weekday: str
    predicted_demand: float
    vs_average_pct: float  # écart à la moyenne (%), + = plus chargé
    suggested_staff: int
    base_staff: int
    delta: int  # personnes en plus/moins vs plancher
    explanation: str


class StaffingPlan(BaseModel):
    days: list[StaffingDay] = []
    average_demand: float
    base_staff: int
    units_per_staff: float
    explanation: str
