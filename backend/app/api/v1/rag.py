"""Endpoints RAG : indexation des factures + question/réponse citée."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.exceptions import PermissionDeniedError
from app.core.security import CurrentUser
from app.intelligence.rag.service import RAGAnswer, answer_question, index_invoice

router = APIRouter(prefix="/rag", tags=["rag"])


class QueryRequest(BaseModel):
    question: str
    k: int = 4


def _require_org(user: CurrentUser) -> int:
    if user.organization_id is None:
        raise PermissionDeniedError("Aucune organisation active")
    return user.organization_id


@router.post("/index/invoices/{invoice_id}")
async def index_invoice_endpoint(
    invoice_id: int,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("invoices")),
) -> dict:
    """Indexe une facture (passages) pour la recherche sémantique."""
    n = await index_invoice(session, organization_id=_require_org(user), invoice_id=invoice_id)
    return {"invoice_id": invoice_id, "chunks_indexed": n}


@router.post("/query", response_model=RAGAnswer)
async def query_endpoint(
    body: QueryRequest,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("invoices")),
) -> RAGAnswer:
    """Question en langage naturel → réponse citée sur les documents de l'org."""
    return await answer_question(
        session, organization_id=_require_org(user), question=body.question, k=body.k
    )
