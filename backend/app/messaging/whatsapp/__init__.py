"""WhatsApp : sélection du client configuré."""

from app.config import settings
from app.messaging.whatsapp.base import SendResult, WhatsAppClient


def get_whatsapp_client() -> WhatsAppClient:
    """Retourne le client WhatsApp configuré (cf. WHATSAPP_PROVIDER)."""
    if settings.whatsapp_provider.lower() == "business_api":
        from app.messaging.whatsapp.business_api import BusinessApiWhatsAppClient

        return BusinessApiWhatsAppClient()
    from app.messaging.whatsapp.mock_client import MockWhatsAppClient

    return MockWhatsAppClient()


__all__ = ["SendResult", "WhatsAppClient", "get_whatsapp_client"]
