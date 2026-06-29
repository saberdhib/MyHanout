"""Dépendances FastAPI partagées (DB, utilisateur courant, RBAC)."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PermissionDeniedError
from app.core.security import DEV_USER, CurrentUser
from app.db.session import get_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


async def get_current_user() -> CurrentUser:
    """Résout l'utilisateur courant.

    MVP : renvoie un utilisateur de dev. À remplacer par la validation d'un
    token (cf. core.security) une fois l'auth implémentée.
    """
    return DEV_USER


def require_permission(scope: str):
    """Fabrique une dépendance RBAC exigeant un scope donné."""

    async def _checker(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not user.has_permission(scope):
            raise PermissionDeniedError(f"Permission requise : {scope}")
        return user

    return _checker
