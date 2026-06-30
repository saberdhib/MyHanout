"""Endpoints signaux : compagnon (météo/tendances du jour) + signaux externes historiques.

- `GET /signals` : météo + tendances « du moment » (mock keyless), pour les recommandations.
- `GET /signals/definitions` : registre des séries externes (point d'extension).
- `GET /signals/observations` : valeurs historiques d'une série (matière à entraîner).
- `POST /signals/ingest` : tire l'historique depuis le provider configuré (idempotent).
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_permission
from app.core.security import CurrentUser
from app.intelligence.signals import SignalsBundle, get_signals
from app.models.signal import SignalDefinition, SignalObservation
from app.schemas.common import ListResponse
from app.schemas.insights import SignalDefinitionOut, SignalIngestResult
from app.services.signals_service import ingest_signals

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=SignalsBundle)
async def signals(_: CurrentUser = Depends(get_current_user)) -> SignalsBundle:
    """Météo + tendances du moment (mock keyless), pour enrichir les recommandations."""
    return get_signals()


@router.get("/definitions", response_model=ListResponse[SignalDefinitionOut])
async def definitions(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> ListResponse[SignalDefinitionOut]:
    """Séries de signaux externes disponibles (météo, vacances, carburant, foot…)."""
    rows = list(
        (await session.scalars(select(SignalDefinition).order_by(SignalDefinition.key))).all()
    )
    items = [
        SignalDefinitionOut(
            key=d.key,
            label=d.label,
            kind=d.kind.value if hasattr(d.kind, "value") else str(d.kind),
            unit=d.unit,
            provider=d.provider,
        )
        for d in rows
    ]
    return ListResponse(items=items, total=len(items))


@router.get("/observations", response_model=list[dict])
async def observations(
    signal_key: str,
    date_from: date | None = None,
    date_to: date | None = None,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> list[dict]:
    """Valeurs historiques d'une série (pour visualiser / entraîner)."""
    stmt = select(SignalObservation).where(SignalObservation.signal_key == signal_key)
    if date_from:
        stmt = stmt.where(SignalObservation.obs_date >= date_from)
    if date_to:
        stmt = stmt.where(SignalObservation.obs_date <= date_to)
    stmt = stmt.order_by(SignalObservation.obs_date)
    rows = list((await session.scalars(stmt)).all())
    return [{"date": o.obs_date.isoformat(), "value": o.value, "region": o.region} for o in rows]


@router.post("/ingest", response_model=SignalIngestResult)
async def ingest(
    date_from: date | None = None,
    date_to: date | None = None,
    region: str | None = None,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("forecasts")),
) -> SignalIngestResult:
    """Récupère l'historique des signaux depuis le provider (mock keyless ou HTTP)."""
    return await ingest_signals(session, date_from=date_from, date_to=date_to, region=region)
