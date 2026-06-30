"""Clé API par commerce — accès programmatique (n8n, Make, Zapier, scripts).

On ne stocke JAMAIS la clé en clair : seul son **hash SHA-256** et un **préfixe**
visible (pour reconnaître la clé dans l'UI). La valeur complète n'est montrée
qu'une fois, à la création.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.tenant import TenantMixin


class ApiKey(Base, TenantMixin, TimestampMixin):
    __tablename__ = "api_key"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))  # libellé ("n8n prod", "Zapier")
    prefix: Mapped[str] = mapped_column(String(16), index=True)  # ex. "mh_a1b2c3d4"
    key_hash: Mapped[str] = mapped_column(String(64), index=True)  # sha256 hex
    # Scopes RBAC séparés par des virgules ; "*" = accès complet de l'org.
    scopes: Mapped[str] = mapped_column(String(255), default="*")
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
