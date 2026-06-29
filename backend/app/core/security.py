"""Sécurité : hachage de mot de passe, JWT (stub), helpers RBAC.

MVP volontairement simple. L'authentification réelle (login, refresh) est à
implémenter ; ici on fournit les primitives et un utilisateur de dev.
"""

from __future__ import annotations

from pydantic import BaseModel


class CurrentUser(BaseModel):
    """Utilisateur courant résolu par la dépendance d'auth."""

    id: int
    email: str
    role: str = "viewer"
    permissions: list[str] = []

    def has_permission(self, scope: str) -> bool:
        return "*" in self.permissions or scope in self.permissions


# Utilisateur de développement (auth réelle à brancher).
DEV_USER = CurrentUser(
    id=1,
    email="admin@myhanout.example",
    role="owner",
    permissions=["*"],
)


def hash_password(password: str) -> str:
    """Hache un mot de passe (passlib/bcrypt)."""
    from passlib.context import CryptContext

    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return ctx.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    from passlib.context import CryptContext

    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    try:
        return ctx.verify(password, hashed)
    except ValueError:
        return False
