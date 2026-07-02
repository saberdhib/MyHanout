"""Déduplication des webhooks entrants (idempotence).

`mark_seen` mémorise l'`external_id` d'un event par source et indique s'il est NOUVEAU.
Un event sans identifiant est traité (impossible de dédupliquer) ; un event déjà vu est
ignoré (retry du fournisseur). Table globale `webhook_inbound`.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.webhook_inbound import WebhookInbound

log = get_logger(__name__)


async def mark_seen(session: AsyncSession, source: str, external_id: str | None) -> bool:
    """Retourne True si l'event est nouveau (à traiter), False s'il a déjà été vu.

    Sans `external_id`, on ne peut pas dédupliquer → on considère l'event comme nouveau.
    """
    if not external_id:
        return True
    existing = await session.scalar(
        select(WebhookInbound).where(
            WebhookInbound.source == source, WebhookInbound.external_id == external_id
        )
    )
    if existing is not None:
        log.info("webhook.duplicate_skipped", source=source, external_id=external_id)
        return False
    session.add(WebhookInbound(source=source, external_id=external_id))
    await session.flush()
    return True
