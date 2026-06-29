"""Client WhatsApp Business API (Meta Cloud API) — stub.

Sans token configuré, erreur explicite. Utiliser WHATSAPP_PROVIDER=mock en local.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.messaging.whatsapp.base import SendResult, WhatsAppClient


class BusinessApiWhatsAppClient(WhatsAppClient):
    name = "business_api"

    def __init__(self) -> None:
        self.token = settings.whatsapp_access_token
        self.phone_id = settings.whatsapp_phone_number_id
        self.base_url = "https://graph.facebook.com/v20.0"

    async def send_text(self, to: str, text: str) -> SendResult:
        if not self.token or not self.phone_id:
            raise RuntimeError("Identifiants WhatsApp manquants. Utilisez WHATSAPP_PROVIDER=mock.")
        url = f"{self.base_url}/{self.phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }
        async with httpx.AsyncClient(timeout=30) as client:  # pragma: no cover
            resp = await client.post(
                url, headers={"Authorization": f"Bearer {self.token}"}, json=payload
            )
            resp.raise_for_status()
            data = resp.json()
        msg_id = data.get("messages", [{}])[0].get("id")
        return SendResult(success=True, message_id=msg_id, provider=self.name)
