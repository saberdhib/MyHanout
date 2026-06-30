"""Chiffrement symétrique des secrets de connecteurs (par commerce).

Clé dérivée de `SECRET_KEY` (déjà présent, défaut dev) via SHA-256 → Fernet.
Aucune nouvelle variable obligatoire : keyless en local, mais **change SECRET_KEY
en production** (sinon les secrets seraient déchiffrables avec la clé par défaut).
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import settings


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    """Chiffre une chaîne (secret connecteur) → token urlsafe."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Déchiffre un token produit par `encrypt`."""
    return _fernet().decrypt(token.encode()).decode()
