"""Service d'authentification : login, refresh, résolution tenant + rôle."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    CurrentUser,
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.models.organization import ROLE_PERMISSIONS, Membership, MembershipRole
from app.models.user import User
from app.repositories.user import UserRepository


async def _memberships(session: AsyncSession, user_id: int) -> list[Membership]:
    return list(
        (await session.scalars(select(Membership).where(Membership.user_id == user_id))).all()
    )


async def resolve_membership(
    session: AsyncSession, user_id: int, org_id: int | None
) -> Membership | None:
    """Retourne le membership pour l'org demandée, sinon le premier disponible.

    Sécurité : on ne fait JAMAIS confiance à un org_id sans vérifier que
    l'utilisateur en est membre.
    """
    memberships = await _memberships(session, user_id)
    if not memberships:
        return None
    if org_id is not None:
        for m in memberships:
            if m.organization_id == org_id:
                return m
        return None  # org demandée mais pas membre -> refus
    return memberships[0]


def to_current_user(user: User, membership: Membership | None) -> CurrentUser:
    if membership is None:
        return CurrentUser(id=user.id, email=user.email, role="viewer", permissions=[])
    role = membership.role
    perms = sorted(ROLE_PERMISSIONS.get(MembershipRole(role), set()))
    return CurrentUser(
        id=user.id,
        email=user.email,
        role=str(role),
        permissions=perms,
        organization_id=membership.organization_id,
    )


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    repo = UserRepository(session)
    user = await repo.get_by_email(email)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def issue_tokens(user: User, membership: Membership | None) -> dict:
    """Génère access + refresh tokens, avec l'organisation active dans le token."""
    org_id = membership.organization_id if membership else None
    extra = {"email": user.email, "org": org_id}
    return {
        "access_token": create_access_token(str(user.id), extra=extra),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
    }
