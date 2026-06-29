"""Service RAG : indexation des factures + question/réponse citée (tenant-scopé)."""

from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.intelligence.llm import LLMMessage, get_llm_provider
from app.intelligence.rag.embeddings import get_embedding_provider
from app.intelligence.rag.store import Chunk, get_vector_store
from app.models.invoice import Invoice, InvoiceLine

log = get_logger(__name__)


class RAGAnswer(BaseModel):
    question: str
    answer: str
    sources: list[Chunk]


def _invoice_chunks(invoice: Invoice, lines: list[InvoiceLine]) -> list[str]:
    """Découpe une facture en passages indexables (explicables)."""
    header = (
        f"Facture {invoice.number or '?'} — fournisseur #{invoice.supplier_id} — "
        f"total {invoice.total_amount} {invoice.currency} — statut {invoice.status}"
    )
    chunks = [header]
    for line in lines:
        chunks.append(
            f"Ligne: {line.description or '?'} — qté {line.quantity} × {line.unit_price} "
            f"= {line.line_total}"
        )
    return chunks


async def index_invoice(session: AsyncSession, *, organization_id: int, invoice_id: int) -> int:
    """Indexe les passages d'une facture dans le vector store. Retourne le nb de chunks."""
    invoice = await session.get(Invoice, invoice_id)  # filtré par tenant
    if not invoice:
        raise NotFoundError(f"Facture {invoice_id} introuvable")
    lines = list(
        (
            await session.scalars(select(InvoiceLine).where(InvoiceLine.invoice_id == invoice_id))
        ).all()
    )
    embedder = get_embedding_provider()
    store = get_vector_store()
    chunks = _invoice_chunks(invoice, lines)
    for content, vector in zip(chunks, embedder.embed_many(chunks), strict=True):
        await store.add(
            session,
            organization_id=organization_id,
            invoice_id=invoice_id,
            content=content,
            embedding=vector,
        )
    log.info("rag.indexed", invoice_id=invoice_id, chunks=len(chunks))
    return len(chunks)


async def answer_question(
    session: AsyncSession, *, organization_id: int, question: str, k: int = 4
) -> RAGAnswer:
    """Recherche les passages pertinents (tenant) puis répond en citant les sources."""
    embedder = get_embedding_provider()
    store = get_vector_store()
    query_vec = embedder.embed(question)
    sources = await store.search(session, organization_id=organization_id, embedding=query_vec, k=k)

    context = "\n".join(f"- {c.content}" for c in sources) or "(aucun document indexé)"
    llm = get_llm_provider()
    response = await llm.complete(
        [
            LLMMessage(
                role="system",
                content="Réponds à la question du commerçant en t'appuyant UNIQUEMENT sur le "
                "contexte fourni. Cite les passages utilisés. Si le contexte est vide, dis-le.",
            ),
            LLMMessage(role="user", content=f"Contexte:\n{context}\n\nQuestion: {question}"),
        ]
    )
    return RAGAnswer(question=question, answer=response.content, sources=sources)
