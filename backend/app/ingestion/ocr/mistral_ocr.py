"""Provider OCR Mistral (implémentation concrète).

Utilise l'API OCR de Mistral (`/v1/ocr`, modèle `mistral-ocr-latest`). Accepte
PDF et images (jpg/png), cas réel d'un commerçant qui photographie sa facture.

Robustesse : timeout, 401 (auth), 429 (quota), erreurs réseau sont converties en
exceptions OCR typées pour permettre un fallback explicite en amont (cf.
`extract_with_fallback`). Sans clé API, lève `OCRAuthError` — la fabrique
`get_ocr_provider` retombe alors sur le mock.
"""

from __future__ import annotations

import base64

import httpx

from app.config import settings
from app.core.logging import get_logger
from app.ingestion.ocr.base import (
    OCRAuthError,
    OCRProvider,
    OCRQuotaError,
    OCRResult,
    OCRTimeoutError,
)

log = get_logger(__name__)

_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


class MistralOCRProvider(OCRProvider):
    name = "mistral"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str = "mistral-ocr-latest",
        endpoint: str = "https://api.mistral.ai/v1/ocr",
        timeout: float = 60.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key or settings.mistral_api_key
        self.model = model
        self.endpoint = endpoint
        self.timeout = timeout
        # Client injectable (tests : httpx.MockTransport, sans réseau).
        self._http_client = http_client

    def _build_document(self, content: bytes, content_type: str) -> dict:
        """Construit le bloc `document` attendu par l'API (PDF ou image)."""
        b64 = base64.b64encode(content).decode()
        if content_type in _IMAGE_TYPES:
            return {"type": "image_url", "image_url": f"data:{content_type};base64,{b64}"}
        # PDF (ou type inconnu) : transmis comme document encodé en base64.
        return {
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{b64}",
        }

    @staticmethod
    def _parse_response(data: dict) -> OCRResult:
        """Mappe la réponse Mistral OCR vers OCRResult (pages markdown)."""
        pages_raw = data.get("pages", []) or []
        pages = [p.get("markdown") or p.get("text") or "" for p in pages_raw]
        text = "\n\n".join(pages).strip()
        # L'API ne fournit pas toujours un score ; confiance haute si du texte sort.
        confidence = 0.9 if text else 0.0
        return OCRResult(
            text=text,
            pages=pages,
            confidence=confidence,
            provider="mistral",
            raw=data,
        )

    async def extract(self, content: bytes, *, content_type: str = "application/pdf") -> OCRResult:
        if not self.api_key:
            raise OCRAuthError("MISTRAL_API_KEY manquante. Utilisez OCR_PROVIDER=mock en local.")

        payload = {"model": self.model, "document": self._build_document(content, content_type)}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        client = self._http_client or httpx.AsyncClient(timeout=self.timeout)
        owns_client = self._http_client is None
        try:
            resp = await client.post(self.endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.TimeoutException as exc:
            log.warning("ocr.mistral.timeout", error=str(exc))
            raise OCRTimeoutError("Délai OCR Mistral dépassé") from exc
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            log.warning("ocr.mistral.http_error", status=code)
            if code == 401:
                raise OCRAuthError("Clé Mistral invalide (401)") from exc
            if code == 429:
                raise OCRQuotaError("Quota Mistral dépassé (429)") from exc
            raise OCRTimeoutError(f"Erreur HTTP Mistral ({code})") from exc
        except httpx.HTTPError as exc:
            log.warning("ocr.mistral.network_error", error=str(exc))
            raise OCRTimeoutError("Erreur réseau OCR Mistral") from exc
        finally:
            if owns_client:
                await client.aclose()

        result = self._parse_response(data)
        log.info("ocr.mistral.done", pages=len(result.pages), chars=len(result.text))
        return result
