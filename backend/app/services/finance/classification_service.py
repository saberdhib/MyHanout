"""Classification des factures (OPEX/CAPEX) — human-in-the-loop, explicable.

Parcours :
1. `suggest_classification` : le classifieur (mock/llm) propose catégorie + kind +
   explication → `classification_source=ai` + confiance. Rien n'est figé.
2. `confirm_classification` : un humain valide/corrige → `source=human`, la
   correction est tracée (audit + table feedback = signal d'apprentissage).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.intelligence.finance import get_expense_classifier
from app.models.base import ClassificationSource, ExpenseKind
from app.models.expense import ExpenseCategory, ExpenseClassificationFeedback
from app.models.invoice import Invoice, InvoiceLine
from app.models.supplier import Supplier

log = get_logger(__name__)


async def _category_by_code(session: AsyncSession, code: str) -> ExpenseCategory | None:
    return await session.scalar(select(ExpenseCategory).where(ExpenseCategory.code == code))


async def suggest_classification(
    session: AsyncSession, *, invoice_id: int, user_id: int | None = None
) -> Invoice:
    """Pose une suggestion IA (catégorie/kind/explication) sur une facture."""
    invoice = await session.get(Invoice, invoice_id)  # filtré par tenant
    if not invoice:
        raise NotFoundError(f"Facture {invoice_id} introuvable")

    supplier_name = None
    if invoice.supplier_id:
        supplier = await session.get(Supplier, invoice.supplier_id)
        supplier_name = supplier.name if supplier else None
    label = await session.scalar(
        select(InvoiceLine.description).where(InvoiceLine.invoice_id == invoice.id).limit(1)
    )

    result = await get_expense_classifier().classify(
        supplier_name=supplier_name,
        label=label,
        total=float(invoice.total_amount) if invoice.total_amount is not None else None,
    )
    category = await _category_by_code(session, result.category_code)

    invoice.category_id = category.id if category else None
    invoice.expense_kind = result.kind
    invoice.classification_source = ClassificationSource.AI
    invoice.classification_confidence = result.confidence
    invoice.classification_explanation = result.explanation  # explication OBLIGATOIRE
    await record_audit(
        session,
        action="invoice.classify.suggest",
        user_id=user_id,
        resource="invoice",
        resource_id=invoice.id,
        detail=f"{result.category_code}/{result.kind.value} conf={result.confidence:.2f}",
    )
    log.info("finance.classify.suggest", invoice_id=invoice.id, code=result.category_code)
    return invoice


async def confirm_classification(
    session: AsyncSession,
    *,
    invoice_id: int,
    category_id: int | None,
    kind: str | None,
    user_id: int | None = None,
    note: str | None = None,
) -> Invoice:
    """Validation/correction humaine → source=human, correction tracée (feedback)."""
    invoice = await session.get(Invoice, invoice_id)
    if not invoice:
        raise NotFoundError(f"Facture {invoice_id} introuvable")

    prev_category_id = invoice.category_id
    prev_kind = invoice.expense_kind
    prev_source = invoice.classification_source

    new_kind = invoice.expense_kind
    if kind is not None:
        new_kind = ExpenseKind(kind)
    elif category_id is not None:
        category = await session.get(ExpenseCategory, category_id)
        if category:
            new_kind = category.kind

    label = "?"
    if category_id is not None:
        invoice.category_id = category_id
        category = await session.get(ExpenseCategory, category_id)
        label = category.label if category else "?"
    invoice.expense_kind = new_kind
    invoice.classification_source = ClassificationSource.HUMAN
    invoice.classification_confidence = 1.0
    invoice.classification_explanation = (
        f"Validé par l'utilisateur : {label} ({new_kind.value})."
        + (f" Note : {note}" if note else "")
    )

    # Signal d'apprentissage : on garde la correction (surtout si elle corrige l'IA).
    session.add(
        ExpenseClassificationFeedback(
            invoice_id=invoice.id,
            previous_category_id=prev_category_id,
            new_category_id=invoice.category_id,
            previous_kind=prev_kind,
            new_kind=new_kind,
            previous_source=prev_source,
            corrected_by_id=user_id,
            note=note,
        )
    )
    await record_audit(
        session,
        action="invoice.classify.confirm",
        user_id=user_id,
        resource="invoice",
        resource_id=invoice.id,
        detail=f"category={invoice.category_id} kind={new_kind.value} (was {prev_kind.value})",
    )
    log.info("finance.classify.confirm", invoice_id=invoice.id, kind=new_kind.value)
    return invoice


async def suggest_all_unclassified(
    session: AsyncSession, *, user_id: int | None = None, limit: int = 100
) -> int:
    """Pose une suggestion IA sur toutes les factures non encore classées."""
    ids = list(
        (
            await session.scalars(
                select(Invoice.id).where(Invoice.expense_kind == ExpenseKind.UNKNOWN).limit(limit)
            )
        ).all()
    )
    for invoice_id in ids:
        await suggest_classification(session, invoice_id=invoice_id, user_id=user_id)
    return len(ids)
