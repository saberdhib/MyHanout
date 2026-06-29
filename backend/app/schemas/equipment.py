"""Schémas équipements / chaîne du froid."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EquipmentStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: str
    location: str | None = None
    min_temp_c: float
    max_temp_c: float
    last_temp_c: float | None = None
    last_recorded_at: datetime | None = None
    status: str  # ok | alert | unknown
    explanation: str


class EquipmentStatusList(BaseModel):
    items: list[EquipmentStatus] = []
    alerts: int = 0
    explanation: str


class PollResult(BaseModel):
    provider: str
    readings: int
    alerts: int
