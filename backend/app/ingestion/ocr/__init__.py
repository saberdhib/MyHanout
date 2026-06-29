"""OCR : abstraction provider + fabrique de sélection."""

from app.config import settings
from app.ingestion.ocr.base import OCRProvider, OCRResult


def get_ocr_provider() -> OCRProvider:
    """Retourne l'implémentation OCR configurée (cf. OCR_PROVIDER)."""
    provider = settings.ocr_provider.lower()
    if provider == "mistral":
        from app.ingestion.ocr.mistral_ocr import MistralOCRProvider

        return MistralOCRProvider()
    if provider == "pdf_fallback":
        from app.ingestion.ocr.pdf_fallback import PdfFallbackProvider

        return PdfFallbackProvider()
    from app.ingestion.ocr.mock_ocr import MockOCRProvider

    return MockOCRProvider()


__all__ = ["OCRProvider", "OCRResult", "get_ocr_provider"]
