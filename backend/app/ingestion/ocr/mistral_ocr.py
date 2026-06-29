"""Provider OCR Mistral (stub).

Squelette d'intégration à l'API Mistral OCR. Sans clé configurée, lève une
erreur explicite — utiliser OCR_PROVIDER=mock en local.
"""

from __future__ import annotations

import base64

import httpx

from app.config import settings
from app.core.logging import get_logger
from app.ingestion.ocr.base import OCRProvider, OCRResult

log = get_logger(__name__)


class MistralOCRProvider(OCRProvider):
    name = "mistral"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.mistral_api_key
        self.endpoint = "https://api.mistral.ai/v1/ocr"

    async def extract(
        self, content: bytes, *, content_type: str = "application/pdf"
    ) -> OCRResult:
        if not self.api_key:
            raise RuntimeError(
                "MISTRAL_API_KEY manquante. Utilisez OCR_PROVIDER=mock en local."
            )
        # TODO: brancher l'appel réel à l'API Mistral OCR.
        # Esquisse de l'appel HTTP pour la future implémentation :
        payload = {
            "document": {
                "type": "document_base64",
                "data": base64.b64encode(content).decode(),
            }
        }
        log.info("ocr.mistral.call", endpoint=self.endpoint, bytes=len(content))
        async with httpx.AsyncClient(timeout=60) as client:  # pragma: no cover
            resp = await client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        text = data.get("text", "")
        return OCRResult(text=text, pages=[text], confidence=0.0, provider=self.name, raw=data)
