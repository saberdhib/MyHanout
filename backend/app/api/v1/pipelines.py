"""Endpoints orchestration data : runs, déclenchement manuel, santé (Data Ops)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.security import CurrentUser
from app.models.base import PipelineTrigger
from app.schemas.common import ListResponse
from app.schemas.dataplatform import PipelineHealth, PipelineRunOut
from app.services import pipeline_service

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


def _out(run) -> PipelineRunOut:
    return PipelineRunOut(
        id=run.id,
        job_name=run.job_name,
        status=str(run.status),
        trigger=str(run.trigger),
        started_at=run.started_at,
        finished_at=run.finished_at,
        data_freshness_at=run.data_freshness_at,
        rows_processed=run.rows_processed,
        error=run.error,
        duration_ms=pipeline_service._duration_ms(run),
    )


@router.get("/runs", response_model=ListResponse[PipelineRunOut])
async def list_runs(
    job: str | None = None,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> ListResponse[PipelineRunOut]:
    runs = await pipeline_service.list_runs(session, job_name=job, status=status, limit=limit)
    items = [_out(r) for r in runs]
    return ListResponse(items=items, total=len(items))


@router.get("/health", response_model=PipelineHealth)
async def health(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> PipelineHealth:
    """Fraîcheur des données + dernier run par job (état du moteur)."""
    return await pipeline_service.health(session)


@router.get("/runs/{run_id}", response_model=PipelineRunOut)
async def get_run(
    run_id: int,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> PipelineRunOut:
    from app.models.pipeline import PipelineRun

    run = await session.get(PipelineRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run introuvable")
    return _out(run)


@router.post("/{job}/trigger", response_model=PipelineRunOut)
async def trigger(
    job: str,
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("forecasts")),
) -> PipelineRunOut:
    """Déclenchement manuel d'un job (human-in-the-loop, Data Ops)."""
    if job not in pipeline_service.available_jobs():
        raise HTTPException(status_code=404, detail=f"Job inconnu : {job}")
    run = await pipeline_service.run_job(
        session, job, trigger=PipelineTrigger.MERCHANT, user_id=user.id
    )
    return _out(run)
