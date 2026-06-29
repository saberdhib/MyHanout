"""Endpoints couche financière (/finance/*) — pré-compta / pilotage.

Permission `finance` (owner + comptable). Tout passe par l'ORM (tenant-scopé).
Chaque réponse porte une `explanation` ; la classification est human-in-the-loop.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.intelligence.finance.alerts import compute_finance_alerts
from app.models.expense import ExpenseCategory
from app.models.invoice import Invoice
from app.schemas.common import ListResponse
from app.schemas.finance import (
    ClassifyConfirmRequest,
    ExpenseCategoryOut,
    FinanceAlerts,
    InventoryValuation,
    InvoiceClassificationOut,
    MarginReport,
    TreasuryView,
)
from app.services.finance.classification_service import (
    confirm_classification,
    suggest_all_unclassified,
    suggest_classification,
)
from app.services.finance.inventory_valuation import compute_inventory_value
from app.services.finance.margin_service import compute_margins
from app.services.finance.treasury_service import compute_treasury

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/treasury", response_model=TreasuryView)
async def treasury(
    date_from: date | None = None,
    date_to: date | None = None,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("finance")),
) -> TreasuryView:
    """Vue de trésorerie estimée (entrées/sorties + alerte cash) sur la période."""
    return await compute_treasury(session, date_from=date_from, date_to=date_to)


@router.get("/inventory-value", response_model=InventoryValuation)
async def inventory_value(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("finance")),
) -> InventoryValuation:
    """Valeur immobilisée du stock (dont part périssable à risque)."""
    return await compute_inventory_value(session)


@router.get("/margins", response_model=MarginReport)
async def margins(
    product_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("finance")),
) -> MarginReport:
    """Marge réelle par produit + signal de dégradation (coût d'achat en hausse)."""
    return await compute_margins(
        session, product_id=product_id, date_from=date_from, date_to=date_to
    )


@router.get("/categories", response_model=ListResponse[ExpenseCategoryOut])
async def categories(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("finance")),
) -> ListResponse[ExpenseCategoryOut]:
    """Référentiel global des catégories de charges (OPEX/CAPEX)."""
    rows = list(
        (await session.scalars(select(ExpenseCategory).order_by(ExpenseCategory.code))).all()
    )
    items = [ExpenseCategoryOut.model_validate(c) for c in rows]
    return ListResponse(items=items, total=len(items))


@router.get("/expenses", response_model=ListResponse[InvoiceClassificationOut])
async def expenses(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("finance")),
) -> ListResponse[InvoiceClassificationOut]:
    """Factures avec leur classification (à valider / corriger)."""
    rows = list((await session.scalars(select(Invoice).order_by(Invoice.id.desc()))).all())
    items = [InvoiceClassificationOut.model_validate(i) for i in rows]
    return ListResponse(items=items, total=len(items))


@router.post("/expenses/classify-all", response_model=dict)
async def classify_all(
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("finance")),
) -> dict:
    """Pose une suggestion IA sur toutes les factures non classées (à valider)."""
    n = await suggest_all_unclassified(session, user_id=user.id)
    return {"classified": n}


@router.post("/invoices/{invoice_id}/classify", response_model=InvoiceClassificationOut)
async def classify(
    invoice_id: int,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("finance")),
) -> InvoiceClassificationOut:
    """Suggestion IA (catégorie/kind/explication) pour une facture."""
    invoice = await suggest_classification(session, invoice_id=invoice_id, user_id=user.id)
    return InvoiceClassificationOut.model_validate(invoice)


@router.post("/invoices/{invoice_id}/classification", response_model=InvoiceClassificationOut)
async def confirm(
    invoice_id: int,
    body: ClassifyConfirmRequest,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("finance")),
) -> InvoiceClassificationOut:
    """Validation/correction humaine de la classification (tracée)."""
    invoice = await confirm_classification(
        session,
        invoice_id=invoice_id,
        category_id=body.category_id,
        kind=body.kind,
        user_id=user.id,
        note=body.note,
    )
    return InvoiceClassificationOut.model_validate(invoice)


@router.get("/alerts", response_model=FinanceAlerts)
async def alerts(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("finance")),
) -> FinanceAlerts:
    """Alertes finance explicables (doublon, anomalie prix, marge, échéance)."""
    return await compute_finance_alerts(session)
