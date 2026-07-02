"""Schémas relance client."""

from __future__ import annotations

from pydantic import BaseModel


class ReengagementCustomer(BaseModel):
    customer_id: int
    name: str | None = None
    phone: str | None = None
    balance: int
    contactable: bool  # opt-in RGPD + téléphone présent


class SegmentOut(BaseModel):
    segment: str
    message: str
    explanation: str
    total: int
    contactable: int
    customers: list[ReengagementCustomer] = []


class SegmentsResponse(BaseModel):
    segments: list[SegmentOut] = []
    disclaimer: str


class SendResult(BaseModel):
    segment: str
    sent: int
    skipped_no_consent: int
    skipped_no_phone: int
    message: str
