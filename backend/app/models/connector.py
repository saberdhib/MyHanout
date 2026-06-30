"""Connecteur configuré **par commerce** (modèle B : self-service).

Chaque org peut brancher son propre WhatsApp/Slack/Telegram : les champs non
sensibles sont en clair (`config`), les secrets sont **chiffrés** (`secret_enc`).
La fabrique de clients lit d'abord la config du tenant, sinon retombe sur le
`.env` global puis le mock (keyless).
"""

from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.tenant import TenantMixin


class TenantConnector(Base, TenantMixin, TimestampMixin):
    __tablename__ = "tenant_connector"

    id: Mapped[int] = mapped_column(primary_key=True)
    # whatsapp | slack | telegram (un par org et par type).
    kind: Mapped[str] = mapped_column(String(32), index=True)
    # Champs non sensibles (JSON) : phone_number_id, verify_token…
    config: Mapped[str] = mapped_column(Text, default="{}")
    # Secrets chiffrés (JSON chiffré) : access_token, app_secret, bot_token…
    secret_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
