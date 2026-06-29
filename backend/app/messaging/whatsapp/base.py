"""Interface abstraite des clients WhatsApp."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class SendResult(BaseModel):
    success: bool
    message_id: str | None = None
    provider: str = "unknown"


class WhatsAppClient(ABC):
    """Contrat commun (mock local / WhatsApp Business API)."""

    name: str = "abstract"

    @abstractmethod
    async def send_text(self, to: str, text: str) -> SendResult:
        """Envoie un message texte à un destinataire."""
        raise NotImplementedError
