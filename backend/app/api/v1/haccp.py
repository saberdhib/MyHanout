"""Endpoints carnet HACCP : plan de nettoyage tracé + registre de conformité."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.exceptions import NotFoundError
from app.core.security import CurrentUser
from app.schemas.common import ListResponse
from app.schemas.haccp import HaccpRegister, HygieneTaskIn, HygieneTaskOut
from app.services import haccp_service

router = APIRouter(prefix="/haccp", tags=["haccp"])


class CompleteBody(BaseModel):
    note: str | None = None


@router.get("/tasks", response_model=ListResponse[HygieneTaskOut])
async def tasks(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> ListResponse[HygieneTaskOut]:
    """Plan de nettoyage (tâches dues en premier). Crée le plan par défaut si vide."""
    created = await haccp_service.bootstrap_default_tasks(session)
    if created:
        await session.commit()
    items = await haccp_service.list_tasks(session)
    return ListResponse(items=items, total=len(items))


@router.post("/tasks", response_model=HygieneTaskOut, status_code=201)
async def create_task(
    body: HygieneTaskIn,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> HygieneTaskOut:
    """Ajoute une tâche d'hygiène récurrente au plan."""
    task = await haccp_service.create_task(session, body)
    await session.commit()
    items = await haccp_service.list_tasks(session)
    created = next((t for t in items if t.id == task.id), None)
    if created is None:
        raise NotFoundError("Tâche introuvable après création")
    return created


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> None:
    """Retire une tâche du plan (l'historique des exécutions part avec elle)."""
    ok = await haccp_service.delete_task(session, task_id)
    if not ok:
        raise NotFoundError("Tâche introuvable")
    await session.commit()


@router.post("/tasks/{task_id}/complete", status_code=204)
async def complete(
    task_id: int,
    body: CompleteBody | None = None,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("stocks")),
) -> None:
    """Trace l'exécution d'une tâche (horodatée, avec l'auteur — preuve HACCP)."""
    record = await haccp_service.complete_task(
        session, task_id, done_by=user.email, note=body.note if body else None
    )
    if record is None:
        raise NotFoundError("Tâche introuvable")
    await session.commit()


@router.get("/register", response_model=HaccpRegister)
async def get_register(
    days: int = Query(default=14, ge=1, le=90),
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> HaccpRegister:
    """Registre consolidé (températures + hygiène) — à présenter en cas de contrôle."""
    return await haccp_service.register(session, days=days)
