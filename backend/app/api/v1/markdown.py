"""Endpoints démarque (anti-gaspillage frais) : liste explicable, scan, appliquer/rejeter."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.exceptions import NotFoundError
from app.core.security import CurrentUser
from app.models.base import MarkdownStatus
from app.models.markdown import MarkdownSuggestion
from app.models.product import Product
from app.schemas.common import ListResponse
from app.schemas.markdown import MarkdownOut
from app.services.markdown_service import compute_markdowns, set_status

router = APIRouter(prefix="/markdown", tags=["markdown"])


def _out(row: MarkdownSuggestion, name: str | None) -> MarkdownOut:
    return MarkdownOut(
        id=row.id,
        product_id=row.product_id,
        product_name=name,
        quantity_at_risk=float(row.quantity_at_risk),
        expiry_date=row.expiry_date.isoformat() if row.expiry_date else None,
        days_to_expiry=row.days_to_expiry,
        current_price=float(row.current_price),
        suggested_price=float(row.suggested_price),
        discount_pct=row.discount_pct,
        expected_units_cleared=row.expected_units_cleared,
        recovered_value=row.recovered_value,
        avoided_loss=row.avoided_loss,
        baseline_loss=row.baseline_loss,
        confidence=row.confidence,
        score=row.score,
        status=str(row.status),
        model_version=row.model_version,
        pipeline_run_id=row.pipeline_run_id,
        explanation=row.explanation,
    )


@router.get("", response_model=ListResponse[MarkdownOut])
async def list_markdowns(
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=300),
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("promos")),
) -> ListResponse[MarkdownOut]:
    """Suggestions de démarque persistées, triées par priorité (perte évitée)."""
    stmt = select(MarkdownSuggestion).order_by(MarkdownSuggestion.score.desc()).limit(limit)
    if status:
        stmt = stmt.where(MarkdownSuggestion.status == status)
    rows = list((await session.scalars(stmt)).all())
    names: dict[int, str] = {}
    pids = [r.product_id for r in rows]
    if pids:
        for pid, name in await session.execute(
            select(Product.id, Product.name).where(Product.id.in_(pids))
        ):
            names[pid] = name
    items = [_out(r, names.get(r.product_id)) for r in rows]
    return ListResponse(items=items, total=len(items))


@router.post("/scan", response_model=ListResponse[MarkdownOut])
async def scan_markdowns(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("promos")),
) -> ListResponse[MarkdownOut]:
    """Recalcule les démarques sur les lots frais à risque et les persiste."""
    await compute_markdowns(session, persist=True)
    await session.commit()
    return await list_markdowns(status=None, limit=100, session=session, _=_)


@router.post("/{suggestion_id}/apply", response_model=MarkdownOut)
async def apply_markdown(
    suggestion_id: int,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("promos")),
) -> MarkdownOut:
    """Applique une démarque (acte le nouveau prix de vente — human-in-the-loop)."""
    row = await set_status(session, suggestion_id, MarkdownStatus.APPLIED)
    if row is None:
        raise NotFoundError("Suggestion de démarque introuvable")
    await session.commit()
    name = await session.scalar(select(Product.name).where(Product.id == row.product_id))
    return _out(row, name)


@router.post("/{suggestion_id}/reject", response_model=MarkdownOut)
async def reject_markdown(
    suggestion_id: int,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("promos")),
) -> MarkdownOut:
    """Écarte une suggestion de démarque (human-in-the-loop)."""
    row = await set_status(session, suggestion_id, MarkdownStatus.REJECTED)
    if row is None:
        raise NotFoundError("Suggestion de démarque introuvable")
    await session.commit()
    name = await session.scalar(select(Product.name).where(Product.id == row.product_id))
    return _out(row, name)
