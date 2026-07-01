"""Endpoints contrôles : 3-way match factures + démarque inconnue."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.schemas.control import InvoiceControlReport, ShrinkageReport
from app.services.control_service import invoice_controls, shrinkage_report

router = APIRouter(prefix="/controls", tags=["controls"])


@router.get("/invoices", response_model=InvoiceControlReport)
async def controls_invoices(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("finance")),
) -> InvoiceControlReport:
    """Écarts facture ↔ dernier coût connu ↔ commande (€ payés en trop)."""
    return await invoice_controls(session)


@router.get("/shrinkage", response_model=ShrinkageReport)
async def controls_shrinkage(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> ShrinkageReport:
    """Démarque inconnue : stock attendu vs réel, valorisée au coût (€ perdus)."""
    return await shrinkage_report(session)
