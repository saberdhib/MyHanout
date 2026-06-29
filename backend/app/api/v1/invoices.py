"""Endpoints factures (lecture)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.repositories.invoice import InvoiceRepository
from app.schemas.common import ListResponse
from app.schemas.invoice import InvoiceOut

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("", response_model=ListResponse[InvoiceOut])
async def list_invoices(
    session: AsyncSession = Depends(get_db),
    _: object = Depends(require_permission("invoices")),
) -> ListResponse[InvoiceOut]:
    repo = InvoiceRepository(session)
    invoices = await repo.list_with_lines()
    items = [InvoiceOut.model_validate(inv) for inv in invoices]
    return ListResponse(items=items, total=len(items))
