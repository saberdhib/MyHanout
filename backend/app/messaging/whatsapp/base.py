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

    async def send_template(
        self, to: str, template: str, params: list[str] | None = None
    ) -> SendResult:
        """Envoie un message template (par défaut : repli sur un message texte)."""
        body = f"[{template}] " + " ".join(params or [])
        return await self.send_text(to, body)

    async def download_media(self, media_id: str) -> bytes:
        """Télécharge un média entrant (image de facture). À surcharger."""
        raise NotImplementedError("download_media non supporté par ce client")
