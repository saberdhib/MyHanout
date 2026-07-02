"""Dépendances FastAPI partagées (DB, utilisateur courant, tenant, RBAC)."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError, PermissionDeniedError
from app.core.security import CurrentUser, JWTError, decode_token, hash_api_key
from app.core.tenancy import set_current_org
from app.db.session import get_session
from app.repositories.user import UserRepository
from app.services.auth_service import resolve_membership, to_current_user

_bearer = HTTPBearer(auto_error=False)


async def _user_from_api_key(session: AsyncSession, api_key: str) -> CurrentUser:
    """Résout un commerce + ses scopes depuis une clé API (X-API-Key)."""
    from datetime import UTC, datetime

    from app.core.tenancy import tenant_context
    from app.models.api_key import ApiKey

    # Lookup par hash, hors garde-fou tenant (on ne connaît pas encore l'org).
    with tenant_context(None):
        key = await session.scalar(
            select(ApiKey).where(
                ApiKey.key_hash == hash_api_key(api_key), ApiKey.revoked.is_(False)
            )
        )
    if key is None:
        raise AuthError("Clé API invalide ou révoquée")
    key.last_used_at = datetime.now(UTC)
    scopes = (
        ["*"]
        if key.scopes.strip() == "*"
        else [s.strip() for s in key.scopes.split(",") if s.strip()]
    )
    set_current_org(key.organization_id)
    return CurrentUser(
        id=key.created_by_user_id or 0,
        email=f"apikey:{key.prefix}",
        role="api",
        permissions=scopes,
        organization_id=key.organization_id,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Résout l'utilisateur + l'organisation courante depuis le Bearer token
    OU une clé API (`X-API-Key`, pour n8n/Make/Zapier/scripts).

    Le tenant courant (organization_id) provient EXCLUSIVEMENT du token / de la clé,
    puis est posé dans le garde-fou central (`set_current_org`) qui filtre toutes les
    requêtes ORM. Le client ne peut pas le falsifier.
    """
    # Accès programmatique par clé API (si pas de Bearer).
    if credentials is None and x_api_key:
        return await _user_from_api_key(session, x_api_key)
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
    # Cycle de vie : un commerce suspendu/résilié (impayé, offboarding) bloque l'accès
    # de ses utilisateurs. Piloté depuis le backoffice plateforme (Lot 2).
    if current.organization_id is not None:
        await _ensure_org_active(session, current.organization_id)
    return current


async def _ensure_org_active(session: AsyncSession, org_id: int) -> None:
    """Refuse l'accès si l'organisation est suspendue ou résiliée."""
    from app.models.organization import Organization, OrgStatus

    org = await session.get(Organization, org_id)
    if org is not None and org.status in (OrgStatus.SUSPENDED, OrgStatus.CANCELLED):
        raise PermissionDeniedError(
            "Accès suspendu : contactez MyHanout pour réactiver votre compte."
        )


def require_permission(scope: str):
    """Fabrique une dépendance RBAC exigeant un scope donné."""

    async def _checker(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not user.has_permission(scope):
            raise PermissionDeniedError(f"Permission requise : {scope}")
        return user

    return _checker
