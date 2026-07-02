"""Stockage d'artefacts de modèles (MLOps) — abstraction + mock keyless par défaut.

Règle d'or (cf. CLAUDE.md §4) : interface ABC + impl **mock par défaut, sans clé, zéro
réseau**. Le mock renvoie une URI déterministe `mock://…` (aucune écriture). L'impl MinIO
(S3-compatible) sérialise réellement les artefacts (prophet/lgbm) ; sans lib/creds →
**fallback mock**.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class ArtifactStore(ABC):
    name: str = "abstract"

    @abstractmethod
    def put(self, key: str, data: bytes, *, content_type: str = "application/json") -> str:
        """Stocke l'artefact et renvoie son URI."""


class MockArtifactStore(ArtifactStore):
    """Défaut keyless : URI déterministe, aucune écriture ni réseau (testable)."""

    name = "mock"

    def put(self, key: str, data: bytes, *, content_type: str = "application/json") -> str:
        return f"mock://{settings.minio_bucket}/{key}"


class MinioArtifactStore(ArtifactStore):
    """MinIO/S3. Requiert `pip install minio` + creds ; sinon fallback mock au put."""

    name = "minio"

    def put(self, key: str, data: bytes, *, content_type: str = "application/json") -> str:
        try:  # pragma: no cover - dépend d'une lib + d'un serveur optionnels
            import io

            from minio import Minio

            client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            if not client.bucket_exists(settings.minio_bucket):
                client.make_bucket(settings.minio_bucket)
            client.put_object(
                settings.minio_bucket,
                key,
                io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            return f"s3://{settings.minio_bucket}/{key}"
        except Exception as exc:  # lib absente / serveur down → on ne casse pas le retrain
            log.warning("artifact_store.fallback", reason=str(exc), to="mock")
            return MockArtifactStore().put(key, data, content_type=content_type)


def get_artifact_store() -> ArtifactStore:
    """Store configuré. Sans MinIO → mock (keyless)."""
    if settings.artifact_store.lower() == "minio" and settings.minio_endpoint:
        return MinioArtifactStore()
    return MockArtifactStore()
