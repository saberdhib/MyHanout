"""Schémas saisie de fin de journée."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.base import DailyEntrySource


class DailyEntryIn(BaseModel):
    product_id: int
    entry_date: date
    quantity_ordered: float = 0
    stock_remaining: float = 0
    source: DailyEntrySource = DailyEntrySource.DASHBOARD


class DailyEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    entry_date: date
    quantity_ordered: float
    stock_remaining: float
    source: str
