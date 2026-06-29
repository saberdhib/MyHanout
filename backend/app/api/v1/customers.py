"""Endpoints clients (avec consentement RGPD explicite)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.models.customer import Customer
from app.schemas.common import ListResponse

router = APIRouter(prefix="/customers", tags=["customers"])


class CustomerIn(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    consent_opt_in: bool = False


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    consent_opt_in: bool


@router.get("", response_model=ListResponse[CustomerOut])
async def list_customers(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> ListResponse[CustomerOut]:
    rows = list((await session.scalars(select(Customer))).all())
    items = [CustomerOut.model_validate(c) for c in rows]
    return ListResponse(items=items, total=len(items))


@router.post("", response_model=CustomerOut, status_code=201)
async def add_customer(
    body: CustomerIn,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> CustomerOut:
    """Ajoute un client ; consent_at horodaté si opt-in (preuve RGPD)."""
    customer = Customer(
        name=body.name,
        phone=body.phone,
        email=body.email,
        consent_opt_in=body.consent_opt_in,
        consent_at=datetime.now(UTC) if body.consent_opt_in else None,
    )
    session.add(customer)
    await session.flush()
    return CustomerOut.model_validate(customer)
