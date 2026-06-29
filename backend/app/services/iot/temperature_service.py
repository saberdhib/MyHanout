"""Suivi de la chaîne du froid : relevés + statut + alertes explicables (HACCP).

Tout tenant-scopé via l'ORM. Les relevés viennent du provider configuré (mock
keyless par défaut). Une dérive hors plage = alerte explicable, jamais d'action
sortante automatique (human-in-the-loop).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.logging import get_logger
from app.ingestion.sensors import get_sensor_provider
from app.models.equipment import Equipment, TemperatureReading
from app.schemas.equipment import EquipmentStatus, EquipmentStatusList, PollResult

log = get_logger(__name__)


def _evaluate(eq: Equipment, temp: float | None, recorded_at: datetime | None) -> EquipmentStatus:
    lo, hi = float(eq.min_temp_c), float(eq.max_temp_c)
    if temp is None:
        status, explanation = "unknown", "Aucun relevé pour le moment."
    elif temp < lo or temp > hi:
        status = "alert"
        explanation = (
            f"{temp:.1f}°C hors plage [{lo:g}…{hi:g}]°C → risque chaîne du froid "
            f"({eq.name}). Vérifier la machine."
        )
    else:
        status = "ok"
        explanation = f"{temp:.1f}°C dans la plage [{lo:g}…{hi:g}]°C."
    return EquipmentStatus(
        id=eq.id,
        name=eq.name,
        kind=eq.kind.value if hasattr(eq.kind, "value") else str(eq.kind),
        location=eq.location,
        min_temp_c=lo,
        max_temp_c=hi,
        last_temp_c=temp,
        last_recorded_at=recorded_at,
        status=status,
        explanation=explanation,
    )


async def _latest_reading(session: AsyncSession, equipment_id: int) -> TemperatureReading | None:
    return await session.scalar(
        select(TemperatureReading)
        .where(TemperatureReading.equipment_id == equipment_id)
        .order_by(TemperatureReading.recorded_at.desc())
        .limit(1)
    )


async def poll_readings(session: AsyncSession, *, user_id: int | None = None) -> PollResult:
    """Relève tous les équipements ayant un capteur, stocke les mesures, compte les alertes."""
    provider = get_sensor_provider()
    equipments = list((await session.scalars(select(Equipment))).all())
    now = datetime.now(UTC)
    readings = 0
    alerts = 0
    for eq in equipments:
        if not eq.sensor_external_id:
            continue
        reading = await provider.read(eq.sensor_external_id, kind=str(eq.kind))
        session.add(
            TemperatureReading(
                equipment_id=eq.id,
                temp_c=reading.temp_c,
                recorded_at=now,
                source=reading.source,
            )
        )
        readings += 1
        if reading.temp_c < float(eq.min_temp_c) or reading.temp_c > float(eq.max_temp_c):
            alerts += 1
    await session.flush()
    await record_audit(
        session,
        action="equipment.poll",
        user_id=user_id,
        resource="equipment",
        detail=f"provider={provider.name} readings={readings} alerts={alerts}",
    )
    log.info("iot.poll", provider=provider.name, readings=readings, alerts=alerts)
    return PollResult(provider=provider.name, readings=readings, alerts=alerts)


async def equipment_status(session: AsyncSession) -> EquipmentStatusList:
    """Statut courant de chaque équipement (dernier relevé + plage), explicable."""
    equipments = list((await session.scalars(select(Equipment).order_by(Equipment.id))).all())
    items: list[EquipmentStatus] = []
    for eq in equipments:
        last = await _latest_reading(session, eq.id)
        items.append(
            _evaluate(
                eq,
                float(last.temp_c) if last else None,
                last.recorded_at if last else None,
            )
        )
    alerts = sum(1 for i in items if i.status == "alert")
    return EquipmentStatusList(
        items=items,
        alerts=alerts,
        explanation=(
            f"{len(items)} équipement(s) suivi(s), {alerts} en alerte. "
            "Relevés du provider capteur (mock si aucun thermomètre connecté)."
        ),
    )
