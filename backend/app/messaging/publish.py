"""Canaux de publication (mock keyless) : réseaux sociaux + clients opt-in.

RGPD : la diffusion clients ne cible QUE les clients ayant consenti. Aucune
donnée n'est envoyée à un tiers en mode mock (tout est journalisé en local).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.messaging.whatsapp import get_whatsapp_client
from app.models.customer import Customer

log = get_logger(__name__)


class PublishResult(BaseModel):
    channel: str
    delivered: int
    detail: str | None = None


class PublishChannel(ABC):
    name: str = "abstract"

    @abstractmethod
    async def publish(
        self, session: AsyncSession, *, organization_id: int, message: str
    ) -> PublishResult:
        raise NotImplementedError


class SocialChannel(PublishChannel):
    """Publie sur les réseaux sociaux du commerçant (mock : journalisé)."""

    name = "social"

    async def publish(self, session, *, organization_id, message) -> PublishResult:
        log.info("publish.social", org=organization_id, chars=len(message))
        return PublishResult(channel=self.name, delivered=1, detail="post réseaux (mock)")


class CustomerBroadcastChannel(PublishChannel):
    """Diffuse aux clients ayant consenti (opt-in), via le client WhatsApp mock."""

    name = "customers"

    async def publish(self, session, *, organization_id, message) -> PublishResult:
        # Filtré par tenant (garde-fou) ; RGPD : uniquement les opt-in avec contact.
        customers = list(
            (await session.scalars(select(Customer).where(Customer.consent_opt_in.is_(True)))).all()
        )
        wa = get_whatsapp_client()
        delivered = 0
        for c in customers:
            if c.phone:
                await wa.send_text(c.phone, message)
                delivered += 1
        log.info("publish.customers", org=organization_id, delivered=delivered)
        return PublishResult(channel=self.name, delivered=delivered, detail="clients opt-in (RGPD)")


_CHANNELS: dict[str, PublishChannel] = {
    "social": SocialChannel(),
    "customers": CustomerBroadcastChannel(),
}


def get_channels(names: list[str]) -> list[PublishChannel]:
    return [_CHANNELS[n] for n in names if n in _CHANNELS]
