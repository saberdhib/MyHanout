"""Authentification du plan « plateforme » (backoffice MyHanout).

⚠️ SÉCURITÉ — c'est l'inverse du garde-fou tenant. Un `PlatformAdmin` peut lire/agir
**au travers de tous les commerces**. Trois règles non négociables :

1. L'identité plateforme est vérifiée en **base** (`platform_admin.is_active`), pas
   seulement via un claim JWT (révocable immédiatement).
2. Le contexte tenant est mis à **None** → le garde-fou ORM ne filtre plus (accès
   cross-tenant volontaire). Aucun `organization_id` client n'est jamais utilisé.
3. Toute action passe par `require_platform_scope(...)` et est **auditée**
   (`services/platform_service.platform_audit`).
"""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.exceptions import AuthError, PermissionDeniedError
from app.core.security import JWTError, decode_token
from app.core.tenancy import set_current_org
from app.models.platform import PLATFORM_ROLE_PERMISSIONS, PlatformAdmin, PlatformRole

_bearer = HTTPBearer(auto_error=False)


class PlatformContext(BaseModel):
    """Opérateur plateforme courant (résolu + vérifié en base)."""

    user_id: int
    email: str
    role: str
    permissions: list[str] = []

    def has_permission(self, scope: str) -> bool:
        return "*" in self.permissions or scope in self.permissions


async def get_platform_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> PlatformContext:
    """Résout l'opérateur plateforme depuis le Bearer et le vérifie en base.

    Pose `current_org = None` : le plan plateforme voit tous les commerces.
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
    # Vérification AUTORITAIRE en base (le claim `plat` n'est qu'un indice UX).
    admin = await session.scalar(
        select(PlatformAdmin).where(
            PlatformAdmin.user_id == user_id, PlatformAdmin.is_active.is_(True)
        )
    )
    if admin is None:
        raise PermissionDeniedError("Accès plateforme requis")

    role = PlatformRole(admin.role)
    perms = sorted(PLATFORM_ROLE_PERMISSIONS.get(role, set()))
    # Cross-tenant : on désactive le filtrage ORM par organisation.
    set_current_org(None)
    return PlatformContext(
        user_id=user_id,
        email=str(payload.get("email", "")),
        role=str(role),
        permissions=perms,
    )


def require_platform_scope(scope: str):
    """Fabrique une dépendance exigeant un scope plateforme (ex. `billing`)."""

    async def _checker(
        admin: PlatformContext = Depends(get_platform_admin),
    ) -> PlatformContext:
        if not admin.has_permission(scope):
            raise PermissionDeniedError(f"Scope plateforme requis : {scope}")
        return admin

    return _checker
