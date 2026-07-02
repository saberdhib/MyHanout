"""MLOps : stockage d'artefacts de modèles (registre → objet sérialisé)."""

from app.intelligence.mlops.storage import ArtifactStore, get_artifact_store

__all__ = ["ArtifactStore", "get_artifact_store"]
