"""Service d'authentification : login, refresh, résolution de l'utilisateur."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    CurrentUser,
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.models.user import User
from app.repositories.user import UserRepository


def _permissions_of(user: User) -> list[str]:
    """Décompose les scopes du rôle (`*` ou liste séparée par virgules)."""
    if not user.role or not user.role.permissions:
        return []
    return [p.strip() for p in user.role.permissions.split(",") if p.strip()]


def to_current_user(user: User) -> CurrentUser:
    return CurrentUser(
        id=user.id,
        email=user.email,
        role=user.role.name if user.role else "viewer",
        permissions=_permissions_of(user),
    )


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    """Vérifie les identifiants ; renvoie l'utilisateur ou None."""
    repo = UserRepository(session)
    user = await repo.get_by_email(email)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def issue_tokens(user: User) -> dict:
    """Génère access + refresh tokens pour un utilisateur authentifié."""
    return {
        "access_token": create_access_token(str(user.id), extra={"email": user.email}),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
    }
