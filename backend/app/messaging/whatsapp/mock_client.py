"""Client WhatsApp mock — journalise au lieu d'envoyer (défaut local/CI)."""

from __future__ import annotations

from app.core.logging import get_logger
from app.messaging.whatsapp.base import SendResult, WhatsAppClient

log = get_logger(__name__)


class MockWhatsAppClient(WhatsAppClient):
    name = "mock"

    def __init__(self) -> None:
        # Boîte d'envoi en mémoire : utile pour les tests/inspection.
        self.outbox: list[tuple[str, str]] = []

    async def send_text(self, to: str, text: str) -> SendResult:
        self.outbox.append((to, text))
        log.info("whatsapp.mock.send", to=to, text=text)
        return SendResult(success=True, message_id=f"mock-{len(self.outbox)}", provider=self.name)

    async def download_media(self, media_id: str) -> bytes:
        """Renvoie un contenu factice : l'OCR mock produira une facture exemple."""
        log.info("whatsapp.mock.download_media", media_id=media_id)
        return b"%PDF-1.4 mock-invoice-image"
