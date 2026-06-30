"""Webhook sortant — MyHanout POSTe ses événements vers une URL externe.

Permet de déclencher n8n / Make / Zapier (ou tout endpoint HTTP) sur les
événements métier (alerte, rupture, reco prête, run terminé). Chaque livraison
est signée HMAC-SHA256 (`X-MyHanout-Signature`) avec le `secret` de l'endpoint.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.tenant import TenantMixin


class WebhookEndpoint(Base, TenantMixin, TimestampMixin):
    __tablename__ = "webhook_endpoint"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(500))
    secret: Mapped[str] = mapped_column(String(64))  # pour signer (HMAC) les livraisons
    # Événements abonnés (CSV) ou "*" pour tous.
    events: Mapped[str] = mapped_column(String(255), default="*")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    # Dernier état de livraison (observabilité légère).
    last_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failures: Mapped[int] = mapped_column(Integer, default=0)
