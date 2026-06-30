"""Schémas analyse forecasting (facteurs externes + effets entre produits)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class FactorInsight(BaseModel):
    signal_key: str
    label: str
    kind: str
    correlation: float  # Pearson r ∈ [-1, 1]
    n: int  # nb de jours appariés
    direction: str  # positive | négative
    strength: str  # faible | modérée | forte | n/a
    verdict: str  # corrélation/coïncidence/données insuffisantes
    explanation: str


class FactorReport(BaseModel):
    product_id: int
    period_from: date
    period_to: date
    factors: list[FactorInsight] = []
    caveat: str
    explanation: str


class ProductRelation(BaseModel):
    product_id: int
    product_name: str | None = None
    correlation: float
    relation: str  # complement | substitute
    strength: str
    explanation: str


class CrossProductReport(BaseModel):
    product_id: int
    period_from: date
    period_to: date
    relations: list[ProductRelation] = []
    caveat: str
    explanation: str


class SignalIngestResult(BaseModel):
    provider: str
    series: int
    observations: int


class SignalDefinitionOut(BaseModel):
    key: str
    label: str
    kind: str
    unit: str | None = None
    provider: str
