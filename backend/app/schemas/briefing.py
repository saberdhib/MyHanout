"""Schémas Pydantic du briefing du matin (tâches du jour consolidées)."""

from __future__ import annotations

from pydantic import BaseModel


class BriefingItemOut(BaseModel):
    id: int
    category: str
    priority: int
    title: str
    detail: str | None = None
    action: str | None = None
    value: float
    entity_type: str | None = None
    entity_id: int | None = None
    done: bool


class BriefingOut(BaseModel):
    id: int
    briefing_date: str | None = None
    summary: str
    total_items: int
    total_value: float
    status: str
    items: list[BriefingItemOut] = []
