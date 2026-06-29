"""Endpoints équipements / chaîne du froid (/equipment/*).

Permission `stocks` (opérations). Relevés via le provider capteur configuré
(mock keyless si aucun thermomètre). Statut + alertes explicables ; aucune
action sortante automatique.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_permission
from app.core.exceptions import PermissionDeniedError
from app.core.security import CurrentUser
from app.models.base import EquipmentKind
from app.models.equipment import Equipment
from app.schemas.equipment import EquipmentStatus, EquipmentStatusList, PollResult
from app.services.iot.temperature_service import equipment_status, poll_readings

router = APIRouter(prefix="/equipment", tags=["equipment"])


class EquipmentCreate(BaseModel):
    name: str
    kind: str = "fridge"
    location: str | None = None
    min_temp_c: float = 0
    max_temp_c: float = 4
    sensor_external_id: str | None = None


def _org(user: CurrentUser) -> int:
    if user.organization_id is None:
        raise PermissionDeniedError("Aucune organisation active")
    return user.organization_id


@router.get("", response_model=EquipmentStatusList)
async def list_status(
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> EquipmentStatusList:
    """Statut courant (dernier relevé + plage) de chaque équipement."""
    return await equipment_status(session)


@router.post("", response_model=EquipmentStatus)
async def create_equipment(
    body: EquipmentCreate,
    session: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_permission("stocks")),
) -> EquipmentStatus:
    """Déclare un équipement à suivre (capteur optionnel)."""
    eq = Equipment(
        name=body.name,
        kind=EquipmentKind(body.kind),
        location=body.location,
        min_temp_c=body.min_temp_c,
        max_temp_c=body.max_temp_c,
        sensor_external_id=body.sensor_external_id,
    )
    session.add(eq)
    await session.flush()
    return EquipmentStatus(
        id=eq.id,
        name=eq.name,
        kind=eq.kind.value,
        location=eq.location,
        min_temp_c=float(eq.min_temp_c),
        max_temp_c=float(eq.max_temp_c),
        status="unknown",
        explanation="Équipement créé — lancez un relevé.",
    )


@router.post("/poll", response_model=PollResult)
async def poll(
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_permission("stocks")),
) -> PollResult:
    """Relève les capteurs (mock keyless ou passerelle réelle) et stocke les mesures."""
    return await poll_readings(session, user_id=user.id)
