"""Notifier : envoie des alertes via le canal configuré (WhatsApp par défaut)."""

from __future__ import annotations

from app.core.logging import get_logger
from app.messaging.whatsapp import get_whatsapp_client

log = get_logger(__name__)


class Notifier:
    """Façade d'envoi de notifications (découple agents/workers du canal)."""

    def __init__(self) -> None:
        self.whatsapp = get_whatsapp_client()

    async def notify(self, to: str, message: str) -> None:
        await self.whatsapp.send_text(to, message)
        log.info("notify.sent", to=to)


def get_notifier() -> Notifier:
    return Notifier()
