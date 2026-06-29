"""Endpoints auth : login (tenant-aware), refresh, utilisateur courant."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.exceptions import AuthError
from app.core.security import CurrentUser, JWTError, create_access_token, decode_token
from app.repositories.user import UserRepository
from app.services.auth_service import authenticate, issue_tokens, resolve_membership

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str
    # Organisation à activer (sinon, première appartenance). Le comptable
    # multi-commerces choisit ainsi son org courante.
    organization_id: int | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    organization_id: int | None = None


class RefreshRequest(BaseModel):
    refresh_token: str
    organization_id: int | None = None


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await authenticate(session, body.email, body.password)
    if not user:
        raise AuthError("Identifiants invalides")
    membership = await resolve_membership(session, user.id, body.organization_id)
    if body.organization_id is not None and membership is None:
        raise AuthError("Vous n'êtes pas membre de cette organisation")
    tokens = issue_tokens(user, membership)
    return TokenResponse(
        **tokens, organization_id=membership.organization_id if membership else None
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, session: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Échange un refresh token valide contre un nouvel access token (org incluse)."""
    try:
        payload = decode_token(body.refresh_token)
    except JWTError as exc:
        raise AuthError("Refresh token invalide ou expiré") from exc
    if payload.get("type") != "refresh":
        raise AuthError("Type de token invalide")

    user_id = int(payload.get("sub", 0))
    user = await UserRepository(session).get_with_role(user_id)
    if not user or not user.is_active:
        raise AuthError("Utilisateur introuvable ou inactif")
    membership = await resolve_membership(session, user_id, body.organization_id)
    org_id = membership.organization_id if membership else None
    return TokenResponse(
        access_token=create_access_token(str(user.id), extra={"email": user.email, "org": org_id}),
        organization_id=org_id,
    )


@router.get("/me", response_model=CurrentUser)
async def me(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return user
