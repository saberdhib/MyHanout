"""Dépendances FastAPI partagées (DB, utilisateur courant, tenant, RBAC)."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError, PermissionDeniedError
from app.core.security import CurrentUser, JWTError, decode_token
from app.core.tenancy import set_current_org
from app.db.session import get_session
from app.repositories.user import UserRepository
from app.services.auth_service import resolve_membership, to_current_user

_bearer = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Résout l'utilisateur + l'organisation courante depuis le Bearer token.

    Le tenant courant (organization_id) provient EXCLUSIVEMENT du token, puis est
    posé dans le garde-fou central (`set_current_org`) qui filtre toutes les
    requêtes ORM. Le client ne peut pas le falsifier.
    """
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

    membership = await resolve_membership(session, user_id, payload.get("org"))
    current = to_current_user(user, membership)
    # Pose le tenant courant pour le garde-fou central (filtre ORM automatique).
    set_current_org(current.organization_id)
    return current


def require_permission(scope: str):
    """Fabrique une dépendance RBAC exigeant un scope donné."""

    async def _checker(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not user.has_permission(scope):
            raise PermissionDeniedError(f"Permission requise : {scope}")
        return user

    return _checker
