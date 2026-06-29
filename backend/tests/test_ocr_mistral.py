"""Tests du provider OCR Mistral — client HTTP mocké (aucun appel réseau)."""

import httpx
import pytest

from app.ingestion.ocr import extract_with_fallback
from app.ingestion.ocr.base import OCRAuthError, OCRQuotaError
from app.ingestion.ocr.mistral_ocr import MistralOCRProvider

_OK_RESPONSE = {
    "pages": [
        {"index": 0, "markdown": "FACTURE\nFournisseur: Boucherie Centrale"},
        {"index": 1, "markdown": "Total TTC: 3840.00 EUR"},
    ],
    "model": "mistral-ocr-latest",
}


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_mistral_ocr_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/ocr")
        assert b"document" in request.content
        return httpx.Response(200, json=_OK_RESPONSE)

    provider = MistralOCRProvider(api_key="sk-test", http_client=_client(handler))
    result = await provider.extract(b"%PDF-1.4 fake", content_type="application/pdf")
    assert result.provider == "mistral"
    assert len(result.pages) == 2
    assert "Boucherie Centrale" in result.text
    assert result.confidence > 0


@pytest.mark.asyncio
async def test_mistral_ocr_image_content_type():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_OK_RESPONSE)

    provider = MistralOCRProvider(api_key="sk-test", http_client=_client(handler))
    await provider.extract(b"\x89PNG fake", content_type="image/png")
    assert captured["body"]["document"]["type"] == "image_url"
    assert captured["body"]["document"]["image_url"].startswith("data:image/png;base64,")


@pytest.mark.asyncio
async def test_mistral_ocr_no_key_raises_auth():
    provider = MistralOCRProvider(api_key="")
    with pytest.raises(OCRAuthError):
        await provider.extract(b"x")


@pytest.mark.asyncio
async def test_mistral_ocr_quota_429():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "rate limited"})

    provider = MistralOCRProvider(api_key="sk-test", http_client=_client(handler))
    with pytest.raises(OCRQuotaError):
        await provider.extract(b"x", content_type="application/pdf")


@pytest.mark.asyncio
async def test_extract_with_fallback_uses_mock_by_default():
    # OCR_PROVIDER=mock (défaut) -> retombe sur le mock, jamais d'appel réseau.
    result = await extract_with_fallback(b"", content_type="application/pdf")
    assert result.provider == "mock"
    assert "FACTURE" in result.text
