"""Schémas Pydantic du Bilan hebdomadaire (agent Bilan)."""

from __future__ import annotations

from pydantic import BaseModel


class TopProduct(BaseModel):
    product_id: int
    name: str | None = None
    revenue: float


class WeeklyReport(BaseModel):
    period_start: str
    period_end: str
    revenue: float
    revenue_prev: float
    revenue_delta_pct: float
    units_sold: float
    gross_margin: float
    gross_margin_pct: float
    top_products: list[TopProduct] = []
    alerts_open: int
    markdown_recovered: float
    orders_suggested: int
    highlights: list[str] = []
    actions: list[str] = []
    narrative: str
