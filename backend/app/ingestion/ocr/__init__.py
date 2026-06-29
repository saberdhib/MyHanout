"""OCR : abstraction provider + fabrique de sélection + extraction résiliente."""

from app.config import settings
from app.core.logging import get_logger
from app.ingestion.ocr.base import (
    OCRAuthError,
    OCRError,
    OCRProvider,
    OCRQuotaError,
    OCRResult,
    OCRTimeoutError,
)

log = get_logger(__name__)


def get_ocr_provider() -> OCRProvider:
    """Retourne l'implémentation OCR configurée (cf. OCR_PROVIDER).

    Si `mistral` est demandé mais qu'aucune clé n'est configurée, on retombe
    proprement sur le mock (le défaut local/CI reste 100 % mock sans clé).
    """
    provider = settings.ocr_provider.lower()
    if provider == "mistral":
        if settings.mistral_api_key:
            from app.ingestion.ocr.mistral_ocr import MistralOCRProvider

            return MistralOCRProvider()
        log.warning("ocr.provider.fallback", reason="no MISTRAL_API_KEY", to="mock")
        provider = "mock"
    if provider == "pdf_fallback":
        from app.ingestion.ocr.pdf_fallback import PdfFallbackProvider

        return PdfFallbackProvider()
    from app.ingestion.ocr.mock_ocr import MockOCRProvider

    return MockOCRProvider()


async def extract_with_fallback(
    content: bytes, *, content_type: str = "application/pdf"
) -> OCRResult:
    """Extrait via le provider configuré, avec fallback explicite si erreur.

    Ordre : provider principal -> pdf_fallback (si PDF) -> mock. Chaque bascule
    est journalisée. Garantit qu'un upload aboutit toujours à un OCRResult.
    """
    provider = get_ocr_provider()
    try:
        return await provider.extract(content, content_type=content_type)
    except OCRError as exc:
        log.warning("ocr.fallback", primary=provider.name, error=type(exc).__name__)

    if content_type == "application/pdf":
        from app.ingestion.ocr.pdf_fallback import PdfFallbackProvider

        try:
            result = await PdfFallbackProvider().extract(content, content_type=content_type)
            if result.text.strip():
                return result
        except OCRError as exc:
            log.warning("ocr.fallback.pdf_failed", error=type(exc).__name__)

    from app.ingestion.ocr.mock_ocr import MockOCRProvider

    return await MockOCRProvider().extract(content, content_type=content_type)


__all__ = [
    "OCRProvider",
    "OCRResult",
    "OCRError",
    "OCRAuthError",
    "OCRQuotaError",
    "OCRTimeoutError",
    "get_ocr_provider",
    "extract_with_fallback",
]
