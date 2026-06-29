"""Chat web : même cerveau (orchestrateur d'agents) que WhatsApp, avec mémoire."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.security import CurrentUser
from app.intelligence.agents.memory import MemoryStore
from app.intelligence.llm.orchestrator import get_orchestrator

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    agent: str
    explanation: str | None = None


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ChatResponse:
    """Conversation depuis le dashboard (orchestrateur + mémoire, tenant-scopé)."""
    subject = f"web:{user.id}"
    memory = MemoryStore(session)
    history = await memory.recall(agent="agent_support", subject=subject, limit=6)
    await memory.remember(agent="agent_support", subject=subject, role="user", content=body.message)
    result = await get_orchestrator().handle(
        body.message, user_id=user.id, data={"history": history}
    )
    await memory.remember(
        agent="agent_support", subject=subject, role="assistant", content=result.reply
    )
    return ChatResponse(reply=result.reply, agent=result.agent, explanation=result.explanation)
