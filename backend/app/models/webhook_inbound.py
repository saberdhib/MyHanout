"""Idempotence des webhooks ENTRANTS (WhatsApp/Slack/Telegram).

Les fournisseurs re-livrent parfois le même event (retries réseau, timeouts). On
mémorise l'identifiant fournisseur (`external_id`) par source pour ne traiter chaque
message qu'une fois. Table **globale** (non tenant : au moment du webhook, aucun tenant
n'est encore résolu).
"""

from __future__ import annotations

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class WebhookInbound(Base, TimestampMixin):
    __tablename__ = "webhook_inbound"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_webhook_inbound_source_ext"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(16), index=True)  # whatsapp | slack | telegram
    external_id: Mapped[str] = mapped_column(String(255), index=True)
