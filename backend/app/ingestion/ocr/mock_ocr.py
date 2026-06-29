"""Provider OCR mock — implémentation par défaut, sans dépendance réseau.

Retourne un texte de facture factice exploitable par le parser. Utilisé en
local et en CI pour faire tourner le pipeline d'ingestion bout-en-bout.
"""

from __future__ import annotations

from app.ingestion.ocr.base import OCRProvider, OCRResult

_SAMPLE = """FACTURE
Fournisseur: Boucherie Centrale
Numero: FAC-2026-0418
Date: 18/04/2026
Echeance: 18/05/2026

Designation            Qte    PU      Total
Boeuf hache            25     88.00   2200.00
Poulet entier          40     41.00   1640.00

Total TTC: 3840.00 EUR
"""


class MockOCRProvider(OCRProvider):
    name = "mock"

    async def extract(self, content: bytes, *, content_type: str = "application/pdf") -> OCRResult:
        return OCRResult(
            text=_SAMPLE,
            pages=[_SAMPLE],
            confidence=0.99,
            provider=self.name,
        )
