"""Schémas Support & mises à jour (Lot 3)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TicketMessageOut(BaseModel):
    id: int
    author_kind: str  # merchant | platform
    author_user_id: int | None = None
    body: str
    created_at: str | None = None


class TicketOut(BaseModel):
    id: int
    subject: str
    category: str | None = None
    status: str
    priority: str
    created_by_user_id: int | None = None
    assigned_admin_id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
    messages: list[TicketMessageOut] = []
    # Renseignés côté backoffice (vue cross-tenant).
    organization_id: int | None = None
    organization_name: str | None = None


class CreateTicketRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=255)
    body: str = Field(min_length=1)
    category: str | None = None
    priority: str = "normal"


class ReplyRequest(BaseModel):
    body: str = Field(min_length=1)


class SetTicketStatusRequest(BaseModel):
    status: str  # open | pending | resolved | closed


class ReleaseNoteOut(BaseModel):
    id: int
    version: str
    title: str
    body: str
    category: str
    published: bool
    published_at: str | None = None
    created_at: str | None = None


class CreateReleaseRequest(BaseModel):
    version: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=3, max_length=255)
    body: str = Field(min_length=1)
    category: str = "feature"
