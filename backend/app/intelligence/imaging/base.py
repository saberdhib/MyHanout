"""Contrat des providers de génération d'images."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class GeneratedImage(BaseModel):
    """Visuel généré, prêt à afficher (data URL) + métadonnées explicables."""

    data_url: str  # ex: "data:image/svg+xml;base64,..." ou "data:image/png;base64,..."
    media_type: str  # "image/svg+xml" | "image/png"
    prompt: str  # le prompt envoyé au modèle (traçabilité / explicabilité)
    provider: str


class ImageProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    async def generate(
        self, prompt: str, *, width: int = 1024, height: int = 1024
    ) -> GeneratedImage:
        """Génère une image à partir d'un prompt textuel."""
        raise NotImplementedError
