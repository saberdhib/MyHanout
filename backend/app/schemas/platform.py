"""Schémas du plan plateforme (backoffice MyHanout)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClientSummary(BaseModel):
    """Ligne de la vue 360 clients (liste)."""

    organization_id: int
    name: str
    slug: str
    business_type: str | None = None
    status: str
    plan: str
    subscription_status: str | None = None
    mrr_eur: float = 0.0
    users: int = 0
    products: int = 0
    sales: int = 0
    created_at: str | None = None


class ClientDetail(ClientSummary):
    """Fiche client détaillée (vue 360)."""

    invoices: int = 0
    connectors_configured: int = 0
    open_tickets: int = 0
    last_sale_at: str | None = None
    trial_ends_on: str | None = None
    started_on: str | None = None
    current_period_end: str | None = None
    notes: str | None = None


class PlatformOverview(BaseModel):
    """Indicateurs agrégés du parc (haut du backoffice)."""

    clients_total: int = 0
    clients_active: int = 0
    clients_trial: int = 0
    clients_suspended: int = 0
    mrr_total_eur: float = 0.0
    arr_total_eur: float = 0.0


class ProvisionClientRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    business_type: str | None = None
    owner_email: str = Field(min_length=3, max_length=255)
    owner_full_name: str | None = None
    owner_password: str = Field(min_length=6, max_length=128)
    plan: str = "trial"


class SetStatusRequest(BaseModel):
    status: str  # active | suspended | cancelled | trial
    reason: str | None = None


class SetPlanRequest(BaseModel):
    plan: str  # trial | starter | pro | enterprise
    mrr_eur: float | None = None
    subscription_status: str | None = None  # trialing | active | past_due | cancelled
    notes: str | None = None
