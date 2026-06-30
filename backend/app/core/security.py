"""Sécurité : hachage de mot de passe, JWT (access/refresh), helpers RBAC."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class CurrentUser(BaseModel):
    """Utilisateur courant résolu par la dépendance d'auth."""

    id: int
    email: str
    role: str = "viewer"
    permissions: list[str] = []
    # Organisation active (tenant courant), issue du token. None si pas de membership.
    organization_id: int | None = None

    def has_permission(self, scope: str) -> bool:
        return "*" in self.permissions or scope in self.permissions


# --- Mots de passe -----------------------------------------------------------


def hash_password(password: str) -> str:
    """Hache un mot de passe (passlib/bcrypt)."""
    return _pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _pwd_context.verify(password, hashed)
    except ValueError:
        return False


# --- JWT ---------------------------------------------------------------------


def _create_token(
    subject: str, *, token_type: str, expires: timedelta, extra: dict | None = None
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, *, extra: dict | None = None) -> str:
    return _create_token(
        subject,
        token_type="access",
        expires=timedelta(minutes=settings.access_token_expire_minutes),
        extra=extra,
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject,
        token_type="refresh",
        expires=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict:
    """Décode et valide un JWT. Lève JWTError si invalide/expiré."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


# --- Clés API (accès programmatique : n8n / Make / Zapier / scripts) ----------
_API_KEY_PREFIX = "mh_"


def generate_api_key() -> tuple[str, str, str]:
    """Génère une clé API → (clé_complète, préfixe_visible, hash_sha256).

    La clé complète n'est montrée qu'une fois (création) ; on ne stocke que le hash.
    """
    full = f"{_API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
    return full, full[:12], hash_api_key(full)


def hash_api_key(full: str) -> str:
    """Hash SHA-256 (hex) d'une clé API."""
    return hashlib.sha256(full.encode()).hexdigest()


__all__ = [
    "CurrentUser",
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "JWTError",
]
