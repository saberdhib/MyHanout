"""Schémas Pydantic du socle data platform (pipelines, reco, alertes)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


# --- Recommandation (moteur de règles) ---
class RecoDecision(BaseModel):
    """Décision produite par le moteur (pure, testable, explicable)."""

    product_id: int
    action: str  # order | reduce | hold
    suggested_quantity: float
    horizon_days: int
    confidence: float
    risk_factor: float
    score: float
    explanation: str
    reasons: list[str] = []
    data_used: dict = {}


class RecommendationOut(BaseModel):
    id: int
    product_id: int
    product_name: str | None = None
    action: str
    suggested_quantity: float
    horizon_days: int
    confidence: float
    risk_factor: float
    score: float
    status: str
    model_version: str
    pipeline_run_id: int | None = None
    explanation: str


class SimulateRequest(BaseModel):
    product_id: int
    quantity: float
    horizon_days: int | None = None


class SimulateResult(BaseModel):
    product_id: int
    ordered_quantity: float
    horizon_days: int
    forecast_demand: float
    current_stock: float
    projected_stock: float
    stockout_risk: float  # 0..1 après commande
    overstock_days: float  # jours de couverture après commande
    explanation: str


# --- Alertes ---
class AlertOut(BaseModel):
    id: int
    kind: str
    priority: str
    status: str
    title: str
    message: str | None = None
    rule: str | None = None
    threshold: float | None = None
    observed_value: float | None = None
    recommended_action: str | None = None
    explanation: str | None = None
    entity_type: str | None = None
    entity_id: int | None = None
    created_at: datetime | None = None


class ResolveAlertRequest(BaseModel):
    note: str | None = None
    dismiss: bool = False  # True = faux positif (status=dismissed)


# --- Pipelines ---
class PipelineRunOut(BaseModel):
    id: int
    job_name: str
    status: str
    trigger: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    data_freshness_at: datetime | None = None
    rows_processed: int
    error: str | None = None
    duration_ms: int | None = None


class PipelineJobHealth(BaseModel):
    job_name: str
    last_status: str | None = None
    last_run_at: datetime | None = None
    data_freshness_at: datetime | None = None
    last_error: str | None = None


class PipelineHealth(BaseModel):
    jobs: list[PipelineJobHealth] = []
    explanation: str
