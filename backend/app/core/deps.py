"""Dépendances FastAPI partagées (DB, utilisateur courant, RBAC)."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError, PermissionDeniedError
from app.core.security import CurrentUser, JWTError, decode_token
from app.db.session import get_session
from app.repositories.user import UserRepository
from app.services.auth_service import to_current_user

_bearer = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Résout l'utilisateur courant à partir d'un Bearer token JWT."""
    if credentials is None:
        raise AuthError("Authentification requise")
    try:
        payload = decode_token(credentials.credentials)
    except JWTError as exc:
        raise AuthError("Token invalide ou expiré") from exc
    if payload.get("type") != "access":
        raise AuthError("Type de token invalide")

    user_id = int(payload.get("sub", 0))
    user = await UserRepository(session).get_with_role(user_id)
    if not user or not user.is_active:
        raise AuthError("Utilisateur introuvable ou inactif")
    return to_current_user(user)


def require_permission(scope: str):
    """Fabrique une dépendance RBAC exigeant un scope donné."""

    async def _checker(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not user.has_permission(scope):
            raise PermissionDeniedError(f"Permission requise : {scope}")
        return user

    return _checker
