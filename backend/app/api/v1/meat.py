"""Endpoints boucherie (/meat/*) : lots, décomposition, rendement, traçabilité."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.schemas.meat import MeatCutIn, MeatLotIn, MeatLotSummary
from app.services.meat_service import create_lot, list_lots, lot_summary, set_breakdown

router = APIRouter(prefix="/meat", tags=["meat"])


class BreakdownRequest(BaseModel):
    cuts: list[MeatCutIn]


class MeatLotRow(BaseModel):
    id: int
    lot_code: str
    species: str
    label: str
    status: str
    gross_weight_kg: float
    purchase_cost: float


@router.get("/lots", response_model=list[MeatLotRow])
async def lots(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> list[MeatLotRow]:
    """Liste des lots (bêtes) reçus."""
    rows = await list_lots(session)
    return [
        MeatLotRow(
            id=lot.id,
            lot_code=lot.lot_code,
            species=lot.species.value,
            label=lot.label,
            status=lot.status.value,
            gross_weight_kg=float(lot.gross_weight_kg),
            purchase_cost=float(lot.purchase_cost),
        )
        for lot in rows
    ]


@router.post("/lots", response_model=MeatLotSummary)
async def create(
    body: MeatLotIn,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("stocks")),
) -> MeatLotSummary:
    """Enregistre une bête achetée au poids (unité de traçabilité)."""
    lot = await create_lot(session, body, user_id=user.id)
    return await lot_summary(session, lot_id=lot.id)


@router.put("/lots/{lot_id}/breakdown", response_model=MeatLotSummary)
async def breakdown(
    lot_id: int,
    body: BreakdownRequest,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("stocks")),
) -> MeatLotSummary:
    """Saisit/ajuste la décomposition (coupes prévu/réel, os/perte)."""
    await set_breakdown(session, lot_id=lot_id, cuts=body.cuts, user_id=user.id)
    return await lot_summary(session, lot_id=lot_id)


@router.get("/lots/{lot_id}", response_model=MeatLotSummary)
async def summary(
    lot_id: int,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> MeatLotSummary:
    """Rendement + allocation de coût/kg + traçabilité d'un lot."""
    return await lot_summary(session, lot_id=lot_id)
