"""Schémas onboarding self-service."""

from __future__ import annotations

from pydantic import BaseModel

from app.models.organization import MembershipRole


class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None
    organization_name: str
    business_type: str | None = None


class SignupResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    organization_id: int


class OrganizationOut(BaseModel):
    id: int
    name: str
    slug: str
    business_type: str | None = None


class ProductIn(BaseModel):
    sku: str
    name: str
    category: str | None = None
    unit: str = "unit"
    unit_price: float | None = None
    perishable: bool = False
    shelf_life_days: int | None = None
    supplier_id: int | None = None


class SupplierIn(BaseModel):
    name: str
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    payment_terms_days: int = 30


class InvitationCreate(BaseModel):
    email: str
    role: MembershipRole = MembershipRole.STAFF


class InvitationOut(BaseModel):
    id: int
    email: str
    role: str
    token: str
    accepted: bool


class InvitationAccept(BaseModel):
    token: str
    password: str
    full_name: str | None = None
