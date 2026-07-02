"""Lecture bornée des téléversements (anti-DoS).

Un fichier trop volumineux (OCR/factures) chargé en mémoire = risque de saturation.
`read_bounded` refuse au-delà de `settings.max_upload_mb` : d'abord via la taille
annoncée (`UploadFile.size`, sans lecture), puis en garde-fou sur le contenu lu.
"""

from __future__ import annotations

from fastapi import UploadFile

from app.config import settings
from app.core.exceptions import PayloadTooLargeError


async def read_bounded(file: UploadFile) -> bytes:
    """Lit le contenu d'un UploadFile en refusant au-delà de la limite configurée."""
    max_bytes = settings.max_upload_mb * 1024 * 1024
    size = getattr(file, "size", None)
    if size is not None and size > max_bytes:
        raise PayloadTooLargeError(f"Fichier trop volumineux (> {settings.max_upload_mb} Mo).")
    content = await file.read()
    if len(content) > max_bytes:
        raise PayloadTooLargeError(f"Fichier trop volumineux (> {settings.max_upload_mb} Mo).")
    return content
