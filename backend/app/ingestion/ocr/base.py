"""Interface abstraite des providers OCR."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class OCRError(Exception):
    """Erreur OCR générique (déclenche un fallback explicite en amont)."""


class OCRAuthError(OCRError):
    """Clé API absente ou invalide."""


class OCRQuotaError(OCRError):
    """Quota/débit dépassé (HTTP 429)."""


class OCRTimeoutError(OCRError):
    """Délai dépassé / erreur réseau."""


class OCRResult(BaseModel):
    """Résultat brut d'un passage OCR sur un document."""

    text: str = Field(description="Texte intégral extrait")
    pages: list[str] = Field(default_factory=list, description="Texte par page")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    provider: str = Field(default="unknown")
    # Données structurées éventuelles (clé/valeur) si le provider en fournit.
    raw: dict = Field(default_factory=dict)


class OCRProvider(ABC):
    """Contrat commun à tous les moteurs OCR (Mistral, fallback, mock...)."""

    name: str = "abstract"

    @abstractmethod
    async def extract(self, content: bytes, *, content_type: str = "application/pdf") -> OCRResult:
        """Extrait le texte d'un document (PDF/image) fourni en octets."""
        raise NotImplementedError
