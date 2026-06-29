"""Service onboarding self-service : signup, invitations, acceptation."""

from __future__ import annotations

import secrets

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.exceptions import AppError, NotFoundError
from app.core.logging import get_logger
from app.core.security import hash_password
from app.models.organization import Invitation, Membership, MembershipRole, Organization
from app.models.user import User

log = get_logger(__name__)


def _slugify(name: str) -> str:
    base = "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
    return base[:48] or "org"


async def _unique_slug(session: AsyncSession, name: str) -> str:
    slug = _slugify(name)
    exists = await session.scalar(
        select(func.count()).select_from(Organization).where(Organization.slug == slug)
    )
    return f"{slug}-{secrets.token_hex(3)}" if exists else slug


async def signup(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    organization_name: str,
    full_name: str | None = None,
    business_type: str | None = None,
) -> tuple[User, Organization, Membership]:
    """Crée user + organisation + membership owner (transaction unique)."""
    existing = await session.scalar(select(User).where(User.email == email))
    if existing:
        raise AppError("Email déjà utilisé", code="email_taken")

    org = Organization(
        name=organization_name,
        slug=await _unique_slug(session, organization_name),
        business_type=business_type,
    )
    user = User(email=email, full_name=full_name, hashed_password=hash_password(password))
    session.add_all([org, user])
    await session.flush()

    membership = Membership(user_id=user.id, organization_id=org.id, role=MembershipRole.OWNER)
    session.add(membership)
    await record_audit(
        session, action="org.signup", user_id=user.id, resource="organization", resource_id=org.id
    )
    log.info("onboarding.signup", org=org.slug, user=email)
    return user, org, membership


async def create_invitation(
    session: AsyncSession,
    *,
    organization_id: int,
    email: str,
    role: MembershipRole,
    invited_by_id: int,
) -> Invitation:
    """Crée une invitation (owner uniquement) pour rejoindre l'organisation."""
    invitation = Invitation(
        organization_id=organization_id,
        email=email,
        role=role,
        token=secrets.token_urlsafe(24),
        invited_by_id=invited_by_id,
    )
    session.add(invitation)
    await record_audit(
        session,
        action="org.invite",
        user_id=invited_by_id,
        resource="invitation",
        detail=f"email={email} role={role.value}",
    )
    await session.flush()
    return invitation


async def accept_invitation(
    session: AsyncSession, *, token: str, password: str, full_name: str | None = None
) -> tuple[User, Membership]:
    """Accepte une invitation : crée/réutilise l'utilisateur et le rattache à l'org."""
    invitation = await session.scalar(select(Invitation).where(Invitation.token == token))
    if not invitation or invitation.accepted:
        raise NotFoundError("Invitation invalide ou déjà utilisée")

    user = await session.scalar(select(User).where(User.email == invitation.email))
    if user is None:
        user = User(
            email=invitation.email,
            full_name=full_name,
            hashed_password=hash_password(password),
        )
        session.add(user)
        await session.flush()

    # Idempotence : pas de doublon de membership.
    existing = await session.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == invitation.organization_id,
        )
    )
    membership = existing or Membership(
        user_id=user.id, organization_id=invitation.organization_id, role=invitation.role
    )
    if existing is None:
        session.add(membership)
    invitation.accepted = True
    await session.flush()
    log.info("onboarding.invite.accepted", org=invitation.organization_id, user=user.email)
    return user, membership
