"""Provider OCR de repli : extraction texte des PDF natifs (pypdf).

Ne fait pas d'OCR image ; utile quand le PDF contient déjà du texte.
"""

from __future__ import annotations

import io

from app.core.logging import get_logger
from app.ingestion.ocr.base import OCRProvider, OCRResult

log = get_logger(__name__)


class PdfFallbackProvider(OCRProvider):
    name = "pdf_fallback"

    async def extract(self, content: bytes, *, content_type: str = "application/pdf") -> OCRResult:
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("pypdf requis pour le fallback PDF") from exc

        reader = PdfReader(io.BytesIO(content))
        pages = [(page.extract_text() or "") for page in reader.pages]
        text = "\n".join(pages)
        log.info("ocr.pdf_fallback.done", pages=len(pages), chars=len(text))
        return OCRResult(
            text=text,
            pages=pages,
            confidence=0.5 if text.strip() else 0.0,
            provider=self.name,
        )
