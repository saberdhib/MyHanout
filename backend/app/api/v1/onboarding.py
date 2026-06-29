"""Endpoints onboarding self-service : signup, setup, invitations."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_permission
from app.core.exceptions import PermissionDeniedError
from app.core.security import CurrentUser
from app.models.product import Product
from app.models.supplier import Supplier
from app.schemas.onboarding import (
    InvitationAccept,
    InvitationCreate,
    InvitationOut,
    ProductIn,
    SignupRequest,
    SignupResponse,
    SupplierIn,
)
from app.services.auth_service import issue_tokens
from app.services.onboarding_service import (
    accept_invitation,
    create_invitation,
    signup,
)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/signup", response_model=SignupResponse)
async def signup_endpoint(
    body: SignupRequest, session: AsyncSession = Depends(get_db)
) -> SignupResponse:
    """Crée un compte + une organisation (l'utilisateur en devient owner)."""
    user, org, membership = await signup(
        session,
        email=body.email,
        password=body.password,
        organization_name=body.organization_name,
        full_name=body.full_name,
        business_type=body.business_type,
    )
    tokens = issue_tokens(user, membership)
    return SignupResponse(**tokens, organization_id=org.id)


@router.post("/suppliers", status_code=201)
async def add_supplier(
    body: SupplierIn,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> dict:
    """Ajoute un fournisseur (rattaché automatiquement à l'org courante)."""
    supplier = Supplier(**body.model_dump())
    session.add(supplier)
    await session.flush()
    return {"id": supplier.id, "name": supplier.name}


@router.post("/products", status_code=201)
async def add_product(
    body: ProductIn,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> dict:
    """Ajoute un produit (rattaché automatiquement à l'org courante)."""
    product = Product(**body.model_dump())
    session.add(product)
    await session.flush()
    return {"id": product.id, "sku": product.sku}


@router.post("/invitations", response_model=InvitationOut)
async def invite(
    body: InvitationCreate,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> InvitationOut:
    """Invite un membre (owner uniquement). Choisit son rôle (ex. comptable)."""
    if user.role != "owner":
        raise PermissionDeniedError("Seul le propriétaire peut inviter des membres")
    if user.organization_id is None:
        raise PermissionDeniedError("Aucune organisation active")
    invitation = await create_invitation(
        session,
        organization_id=user.organization_id,
        email=body.email,
        role=body.role,
        invited_by_id=user.id,
    )
    return InvitationOut(
        id=invitation.id,
        email=invitation.email,
        role=str(invitation.role),
        token=invitation.token,
        accepted=invitation.accepted,
    )


@router.post("/invitations/accept", response_model=SignupResponse)
async def accept(body: InvitationAccept, session: AsyncSession = Depends(get_db)) -> SignupResponse:
    """Accepte une invitation : rejoint l'organisation avec le rôle défini."""
    from app.repositories.user import UserRepository

    user, membership = await accept_invitation(
        session, token=body.token, password=body.password, full_name=body.full_name
    )
    full_user = await UserRepository(session).get_with_role(user.id)
    assert full_user is not None  # vient d'être créé/retrouvé
    tokens = issue_tokens(full_user, membership)
    return SignupResponse(**tokens, organization_id=membership.organization_id)
