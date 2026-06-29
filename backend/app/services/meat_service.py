"""Boucherie : lots (bête au poids) → coupes → rendement + allocation de coût.

Logique métier :
- on achète une bête à un poids brut et un coût ;
- on saisit les coupes (prévu, puis réel) ; l'os/la perte est marqué `is_waste` ;
- le **rendement** = poids valorisable / poids brut ;
- le **coût au kilo valorisable** = coût d'achat / poids valorisable réel ;
- chaque coupe se voit **allouer un coût** = coût/kg × poids réel (hors perte).
Tout est tenant-scopé et tracé (lot_code → fournisseur → date).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.base import MeatLotStatus, MeatSpecies
from app.models.meat import MeatCut, MeatLot
from app.models.supplier import Supplier
from app.schemas.meat import MeatCutIn, MeatCutOut, MeatLotIn, MeatLotSummary

log = get_logger(__name__)


async def create_lot(
    session: AsyncSession, data: MeatLotIn, *, user_id: int | None = None
) -> MeatLot:
    lot = MeatLot(
        lot_code=data.lot_code,
        species=MeatSpecies(data.species),
        label=data.label,
        supplier_id=data.supplier_id,
        gross_weight_kg=data.gross_weight_kg,
        purchase_cost=data.purchase_cost,
        received_at=data.received_at or datetime.now(UTC),
        notes=data.notes,
        status=MeatLotStatus.RECEIVED,
    )
    session.add(lot)
    await session.flush()
    await record_audit(
        session,
        action="meat.lot.create",
        user_id=user_id,
        resource="meat_lot",
        resource_id=lot.id,
        detail=f"{data.label} {data.gross_weight_kg}kg code={data.lot_code}",
    )
    log.info("meat.lot.create", lot_id=lot.id, code=data.lot_code)
    return lot


async def set_breakdown(
    session: AsyncSession, *, lot_id: int, cuts: list[MeatCutIn], user_id: int | None = None
) -> MeatLot:
    """Remplace la décomposition d'un lot (prévu/réel). Passe le statut à breaking/done."""
    lot = await session.get(MeatLot, lot_id)
    if not lot:
        raise NotFoundError(f"Lot {lot_id} introuvable")

    existing = list((await session.scalars(select(MeatCut).where(MeatCut.lot_id == lot_id))).all())
    for c in existing:
        await session.delete(c)
    await session.flush()

    any_actual = False
    for cut_in in cuts:
        if cut_in.actual_weight_kg is not None:
            any_actual = True
        session.add(
            MeatCut(
                lot_id=lot.id,
                product_id=cut_in.product_id,
                cut_label=cut_in.cut_label,
                expected_weight_kg=cut_in.expected_weight_kg,
                actual_weight_kg=cut_in.actual_weight_kg,
                is_waste=cut_in.is_waste,
            )
        )
    lot.status = MeatLotStatus.DONE if any_actual else MeatLotStatus.BREAKING
    await session.flush()
    await record_audit(
        session,
        action="meat.lot.breakdown",
        user_id=user_id,
        resource="meat_lot",
        resource_id=lot.id,
        detail=f"cuts={len(cuts)} status={lot.status.value}",
    )
    log.info("meat.lot.breakdown", lot_id=lot.id, cuts=len(cuts))
    return lot


async def lot_summary(session: AsyncSession, *, lot_id: int) -> MeatLotSummary:
    """Calcule rendement + allocation de coût + traçabilité pour un lot."""
    lot = await session.get(MeatLot, lot_id)
    if not lot:
        raise NotFoundError(f"Lot {lot_id} introuvable")
    cuts = list((await session.scalars(select(MeatCut).where(MeatCut.lot_id == lot_id))).all())

    gross = float(lot.gross_weight_kg or 0)
    cost = float(lot.purchase_cost or 0)
    saleable = sum(float(c.actual_weight_kg or 0) for c in cuts if not c.is_waste)
    waste = sum(float(c.actual_weight_kg or 0) for c in cuts if c.is_waste)
    cost_per_kg = (cost / saleable) if saleable else None
    yield_pct = (saleable / gross) if gross else None

    cut_out: list[MeatCutOut] = []
    for c in cuts:
        actual = float(c.actual_weight_kg or 0)
        allocated = (cost_per_kg * actual) if (cost_per_kg and not c.is_waste) else None
        cut_out.append(
            MeatCutOut(
                id=c.id,
                cut_label=c.cut_label,
                product_id=c.product_id,
                expected_weight_kg=(float(c.expected_weight_kg) if c.expected_weight_kg else None),
                actual_weight_kg=(actual or None),
                is_waste=c.is_waste,
                allocated_cost=(round(allocated, 2) if allocated is not None else None),
                cost_per_kg=(round(cost_per_kg, 2) if cost_per_kg else None),
                explanation=(
                    f"{actual:g} kg × {cost_per_kg:.2f} €/kg valorisable"
                    if allocated is not None
                    else ("Os / perte : hors valorisation" if c.is_waste else "Réel non saisi")
                ),
            )
        )

    supplier_name = None
    if lot.supplier_id:
        supplier = await session.get(Supplier, lot.supplier_id)
        supplier_name = supplier.name if supplier else None

    return MeatLotSummary(
        id=lot.id,
        lot_code=lot.lot_code,
        species=lot.species.value,
        label=lot.label,
        status=lot.status.value,
        supplier_id=lot.supplier_id,
        gross_weight_kg=gross,
        purchase_cost=cost,
        saleable_weight_kg=round(saleable, 3),
        waste_weight_kg=round(waste, 3),
        yield_pct=(round(yield_pct, 4) if yield_pct is not None else None),
        cost_per_kg=(round(cost_per_kg, 2) if cost_per_kg else None),
        cuts=cut_out,
        traceability=(
            f"Lot {lot.lot_code} ({lot.label}, {lot.species.value}) — "
            f"fournisseur {supplier_name or 'n/a'} — reçu le {lot.received_at:%Y-%m-%d}."
        ),
        explanation=(
            f"Rendement {yield_pct * 100:.0f}% ({saleable:g}/{gross:g} kg valorisables) ; "
            f"coût {cost_per_kg:.2f} €/kg."
            if (yield_pct is not None and cost_per_kg is not None)
            else "Saisir les poids réels des coupes pour calculer rendement et coût/kg."
        ),
    )


async def list_lots(session: AsyncSession) -> list[MeatLot]:
    return list((await session.scalars(select(MeatLot).order_by(MeatLot.received_at.desc()))).all())
