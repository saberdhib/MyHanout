"""Schémas fidélité client."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoyaltyTxnOut(BaseModel):
    id: int
    kind: str  # earn | redeem | adjust
    points: int
    amount: float | None = None
    reason: str
    created_at: str | None = None


class LoyaltyAccountOut(BaseModel):
    customer_id: int
    customer_name: str | None = None
    points_balance: int
    lifetime_points: int
    reward_ready: bool
    points_to_next: int
    rewards_available: int
    explanation: str


class LoyaltyDetailOut(LoyaltyAccountOut):
    transactions: list[LoyaltyTxnOut] = []


class EarnRequest(BaseModel):
    amount: float = Field(gt=0, description="Montant d'achat (€) attribué au client.")
    reason: str | None = None


class RedeemResult(BaseModel):
    customer_id: int
    reward_label: str
    points_spent: int
    points_balance: int
    explanation: str
