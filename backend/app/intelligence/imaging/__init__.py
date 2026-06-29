"""Génération de visuels (text-to-image) derrière une abstraction + mock keyless.

Cas d'usage démo : générer une **affiche promo** anti-gaspillage pour un produit
en fin de vie. Sans clé → `MockImageProvider` (affiche SVG déterministe, zéro
réseau). Avec clé HuggingFace → modèle text-to-image (Stable Diffusion).
"""

from __future__ import annotations

from app.config import settings
from app.core.logging import get_logger
from app.intelligence.imaging.base import GeneratedImage, ImageProvider
from app.intelligence.imaging.mock import MockImageProvider

log = get_logger(__name__)


def get_image_provider() -> ImageProvider:
    """Retourne le provider d'images configuré. Sans clé → mock (keyless)."""
    provider = settings.image_provider.lower()
    if provider == "huggingface" and settings.huggingface_api_key:
        from app.intelligence.imaging.huggingface import HuggingFaceImageProvider

        return HuggingFaceImageProvider()
    if provider == "huggingface":
        log.warning("imaging.provider.fallback", reason="no key", to="mock")
    return MockImageProvider()


__all__ = ["GeneratedImage", "ImageProvider", "get_image_provider"]
