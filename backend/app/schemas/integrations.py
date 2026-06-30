"""Schémas ouverture : clés API + webhooks sortants (n8n / Make / Zapier)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ApiKeyOut(BaseModel):
    id: int
    name: str
    prefix: str  # préfixe visible (la clé complète n'est jamais re-affichée)
    scopes: str
    revoked: bool
    last_used_at: datetime | None = None
    created_at: datetime | None = None


class ApiKeyCreated(ApiKeyOut):
    """Retourné UNIQUEMENT à la création : contient la clé en clair (à copier)."""

    key: str


class ApiKeyCreate(BaseModel):
    name: str
    scopes: str = "*"  # CSV de scopes RBAC, ou "*" pour accès complet


class WebhookOut(BaseModel):
    id: int
    url: str
    events: str
    active: bool
    last_status: int | None = None
    last_delivered_at: datetime | None = None
    failures: int = 0
    created_at: datetime | None = None


class WebhookCreate(BaseModel):
    url: str
    events: str = "*"  # CSV d'événements ou "*"
    secret: str | None = None  # généré si absent


class WebhookCreated(WebhookOut):
    secret: str  # montré à la création (pour vérifier la signature côté n8n/Make)
