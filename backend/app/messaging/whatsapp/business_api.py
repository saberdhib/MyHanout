"""Client WhatsApp Business API (Meta Cloud API).

Implémentation concrète : envoi texte/template, téléchargement de média,
retry simple sur erreurs transitoires. Sans token configuré → erreur explicite
(la fabrique retombe alors sur le mock).
"""

from __future__ import annotations

import asyncio

import httpx

from app.config import settings
from app.core.logging import get_logger
from app.messaging.whatsapp.base import SendResult, WhatsAppClient

log = get_logger(__name__)

_MAX_RETRIES = 3


class BusinessWhatsAppClient(WhatsAppClient):
    name = "business"

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self.token = settings.whatsapp_access_token
        self.phone_id = settings.whatsapp_phone_number_id
        self.base_url = f"https://graph.facebook.com/{settings.graph_api_version}"
        self._http_client = http_client

    def _require_creds(self) -> None:
        if not self.token or not self.phone_id:
            raise RuntimeError("Identifiants WhatsApp manquants. Utilisez WHATSAPP_PROVIDER=mock.")

    async def _post(self, url: str, payload: dict) -> dict:
        """POST avec retry exponentiel sur erreurs réseau / 429 / 5xx."""
        client = self._http_client or httpx.AsyncClient(timeout=30)
        owns = self._http_client is None
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            for attempt in range(1, _MAX_RETRIES + 1):
                try:
                    resp = await client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    return resp.json()
                except httpx.HTTPStatusError as exc:
                    code = exc.response.status_code
                    if code in (429, 500, 502, 503) and attempt < _MAX_RETRIES:
                        wait = 2**attempt
                        log.warning("whatsapp.retry", status=code, attempt=attempt, wait=wait)
                        await asyncio.sleep(wait)
                        continue
                    log.warning("whatsapp.http_error", status=code)
                    raise
                except httpx.HTTPError as exc:
                    if attempt < _MAX_RETRIES:
                        await asyncio.sleep(2**attempt)
                        continue
                    log.warning("whatsapp.network_error", error=str(exc))
                    raise
            raise RuntimeError("WhatsApp: échec après retries")
        finally:
            if owns:
                await client.aclose()

    async def send_text(self, to: str, text: str) -> SendResult:
        self._require_creds()
        data = await self._post(
            f"{self.base_url}/{self.phone_id}/messages",
            {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}},
        )
        msg_id = data.get("messages", [{}])[0].get("id")
        log.info("whatsapp.business.sent", to=to, message_id=msg_id)
        return SendResult(success=True, message_id=msg_id, provider=self.name)

    async def send_template(
        self, to: str, template: str, params: list[str] | None = None
    ) -> SendResult:
        self._require_creds()
        components = (
            [{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}]
            if params
            else []
        )
        data = await self._post(
            f"{self.base_url}/{self.phone_id}/messages",
            {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {
                    "name": template,
                    "language": {"code": "fr"},
                    "components": components,
                },
            },
        )
        msg_id = data.get("messages", [{}])[0].get("id")
        return SendResult(success=True, message_id=msg_id, provider=self.name)

    async def download_media(self, media_id: str) -> bytes:
        """Récupère l'URL du média puis télécharge son contenu binaire."""
        self._require_creds()
        client = self._http_client or httpx.AsyncClient(timeout=30)
        owns = self._http_client is None
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            meta = await client.get(f"{self.base_url}/{media_id}", headers=headers)
            meta.raise_for_status()
            media_url = meta.json()["url"]
            binary = await client.get(media_url, headers=headers)
            binary.raise_for_status()
            log.info(
                "whatsapp.business.download_media", media_id=media_id, bytes=len(binary.content)
            )
            return binary.content
        finally:
            if owns:
                await client.aclose()
