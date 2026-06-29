"""Fournisseur d'embeddings (abstraction + mock déterministe par défaut).

Le mock est sans réseau et déterministe (hashing de tokens → vecteur normalisé),
suffisant pour le RAG local/CI et les tests. Un provider réel (Mistral/embedding
API) se branche derrière la même interface, sélectionné par env si une clé existe.
"""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod

from app.config import settings
from app.intelligence.rag import EMBED_DIM


class EmbeddingProvider(ABC):
    name: str = "abstract"
    dim: int = EMBED_DIM

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class MockEmbeddingProvider(EmbeddingProvider):
    """Embedding déterministe par sac de tokens hashés, vecteur normalisé L2."""

    name = "mock"

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in text.lower().split():
            h = int(hashlib.sha256(token.encode()).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


def get_embedding_provider() -> EmbeddingProvider:
    """Retourne le provider configuré. Sans clé → mock (défaut keyless)."""
    provider = getattr(settings, "embedding_provider", "mock").lower()
    if provider == "mistral" and settings.mistral_api_key:
        # Implémentation réelle à brancher (API embeddings) ; mock par défaut.
        return MockEmbeddingProvider()
    return MockEmbeddingProvider()
