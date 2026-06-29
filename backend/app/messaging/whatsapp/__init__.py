"""WhatsApp : sélection du client configuré."""

from app.config import settings
from app.messaging.whatsapp.base import SendResult, WhatsAppClient


def get_whatsapp_client() -> WhatsAppClient:
    """Retourne le client WhatsApp configuré (cf. WHATSAPP_PROVIDER).

    `business` requiert un token ; sinon on retombe sur le mock (défaut local/CI).
    """
    provider = settings.whatsapp_provider.lower()
    if provider in ("business", "business_api"):
        if settings.whatsapp_access_token and settings.whatsapp_phone_number_id:
            from app.messaging.whatsapp.business_api import BusinessWhatsAppClient

            return BusinessWhatsAppClient()
        from app.core.logging import get_logger

        get_logger(__name__).warning(
            "whatsapp.provider.fallback", reason="no credentials", to="mock"
        )
    from app.messaging.whatsapp.mock_client import MockWhatsAppClient

    return MockWhatsAppClient()


__all__ = ["SendResult", "WhatsAppClient", "get_whatsapp_client"]
