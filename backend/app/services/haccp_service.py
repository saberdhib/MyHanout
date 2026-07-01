"""Carnet HACCP : plan de nettoyage tracé + conformité de la chaîne du froid.

Réutilise les relevés de température existants (Equipment/TemperatureReading, posés
par le provider capteurs) et ajoute la traçabilité hygiène (tâches récurrentes,
exécutions horodatées). Le **registre** consolide le tout : c'est la pièce à montrer
en cas de contrôle sanitaire.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.equipment import Equipment, TemperatureReading
from app.models.haccp import HygieneRecord, HygieneTask
from app.schemas.haccp import (
    EquipmentCompliance,
    HaccpRegister,
    HygieneRecordOut,
    HygieneTaskIn,
    HygieneTaskOut,
)

# Fenêtre (jours) pendant laquelle une exécution couvre la fréquence.
_FREQ_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}

# Plan de nettoyage par défaut (proposé au premier usage / seed).
DEFAULT_TASKS: list[tuple[str, str]] = [
    ("Nettoyage des surfaces de travail", "daily"),
    ("Contrôle visuel des dates (DLC) en rayon", "daily"),
    ("Désinfection de la chambre froide", "weekly"),
    ("Dégivrage et nettoyage du congélateur", "monthly"),
]


async def _last_records(session: AsyncSession, task_ids: list[int]) -> dict[int, HygieneRecord]:
    """Dernière exécution par tâche."""
    if not task_ids:
        return {}
    rows = await session.scalars(
        select(HygieneRecord)
        .where(HygieneRecord.task_id.in_(task_ids))
        .order_by(HygieneRecord.done_at.asc())
    )
    latest: dict[int, HygieneRecord] = {}
    for rec in rows:
        latest[rec.task_id] = rec  # trié ascendant → le dernier écrase
    return latest


def _is_due(task: HygieneTask, last: HygieneRecord | None, now: datetime) -> bool:
    if last is None:
        return True
    window = timedelta(days=_FREQ_DAYS.get(task.frequency, 1))
    done_at = last.done_at if last.done_at.tzinfo else last.done_at.replace(tzinfo=UTC)
    return now - done_at >= window


async def list_tasks(session: AsyncSession, *, now: datetime | None = None) -> list[HygieneTaskOut]:
    now = now or datetime.now(UTC)
    tasks = list(
        (await session.scalars(select(HygieneTask).where(HygieneTask.active.is_(True)))).all()
    )
    latest = await _last_records(session, [t.id for t in tasks])
    out = [
        HygieneTaskOut(
            id=t.id,
            name=t.name,
            frequency=t.frequency,
            active=t.active,
            notes=t.notes,
            due=_is_due(t, latest.get(t.id), now),
            last_done_at=latest[t.id].done_at.isoformat() if t.id in latest else None,
            last_done_by=latest[t.id].done_by if t.id in latest else None,
        )
        for t in tasks
    ]
    out.sort(key=lambda t: (not t.due, t.name))
    return out


async def create_task(session: AsyncSession, data: HygieneTaskIn) -> HygieneTask:
    if data.frequency not in _FREQ_DAYS:
        raise ValueError(f"Fréquence inconnue : {data.frequency}")
    task = HygieneTask(name=data.name, frequency=data.frequency, notes=data.notes)
    session.add(task)
    await session.flush()
    return task


async def delete_task(session: AsyncSession, task_id: int) -> bool:
    task = await session.get(HygieneTask, task_id)
    if task is None:
        return False
    await session.delete(task)
    await session.flush()
    return True


async def complete_task(
    session: AsyncSession,
    task_id: int,
    *,
    done_by: str | None = None,
    note: str | None = None,
) -> HygieneRecord | None:
    task = await session.get(HygieneTask, task_id)
    if task is None:
        return None
    record = HygieneRecord(task_id=task_id, done_at=datetime.now(UTC), done_by=done_by, note=note)
    session.add(record)
    await session.flush()
    return record


async def bootstrap_default_tasks(session: AsyncSession) -> int:
    """Crée le plan de nettoyage par défaut si le commerce n'en a aucun."""
    existing = (await session.scalars(select(HygieneTask.id).limit(1))).first()
    if existing is not None:
        return 0
    for name, freq in DEFAULT_TASKS:
        session.add(HygieneTask(name=name, frequency=freq))
    await session.flush()
    return len(DEFAULT_TASKS)


async def temperature_compliance(
    session: AsyncSession, *, days: int = 7, now: datetime | None = None
) -> list[EquipmentCompliance]:
    """Taux de conformité des relevés par équipement sur la période."""
    now = now or datetime.now(UTC)
    since = now - timedelta(days=days)
    equipments = list((await session.scalars(select(Equipment))).all())
    out: list[EquipmentCompliance] = []
    for eq in equipments:
        readings = list(
            (
                await session.scalars(
                    select(TemperatureReading)
                    .where(
                        TemperatureReading.equipment_id == eq.id,
                        TemperatureReading.recorded_at >= since,
                    )
                    .order_by(TemperatureReading.recorded_at.asc())
                )
            ).all()
        )
        lo, hi = float(eq.min_temp_c), float(eq.max_temp_c)
        in_range = sum(1 for r in readings if lo <= float(r.temp_c) <= hi)
        breaches = [
            f"{r.recorded_at:%d/%m %H:%M} : {float(r.temp_c):.1f}°C (plage {lo:g}–{hi:g}°C)"
            for r in readings
            if not (lo <= float(r.temp_c) <= hi)
        ][-5:]
        last = readings[-1] if readings else None
        out.append(
            EquipmentCompliance(
                equipment_id=eq.id,
                equipment_name=eq.name,
                min_temp_c=lo,
                max_temp_c=hi,
                readings=len(readings),
                in_range=in_range,
                compliance_pct=round(in_range / len(readings) * 100, 1) if readings else 100.0,
                last_temp_c=float(last.temp_c) if last else None,
                last_at=last.recorded_at.isoformat() if last else None,
                breaches=breaches,
            )
        )
    return out


async def register(
    session: AsyncSession, *, days: int = 14, now: datetime | None = None
) -> HaccpRegister:
    """Registre consolidé (températures + hygiène) — la pièce du contrôle sanitaire."""
    now = now or datetime.now(UTC)
    since = now - timedelta(days=days)

    temperature = await temperature_compliance(session, days=days, now=now)

    records = list(
        (
            await session.scalars(
                select(HygieneRecord)
                .where(HygieneRecord.done_at >= since)
                .order_by(HygieneRecord.done_at.desc())
            )
        ).all()
    )
    task_names = {t.id: t.name for t in (await session.scalars(select(HygieneTask))).all()}
    hygiene = [
        HygieneRecordOut(
            id=r.id,
            task_id=r.task_id,
            task_name=task_names.get(r.task_id),
            done_at=r.done_at.isoformat(),
            done_by=r.done_by,
            note=r.note,
        )
        for r in records
    ]

    tasks = await list_tasks(session, now=now)
    due = sum(1 for t in tasks if t.due)
    avg = (
        round(sum(t.compliance_pct for t in temperature) / len(temperature), 1)
        if temperature
        else 100.0
    )
    return HaccpRegister(
        period_days=days,
        generated_at=now.isoformat(),
        temperature=temperature,
        hygiene=hygiene,
        tasks_due=due,
        explanation=(
            f"Sur {days} j : conformité température moyenne {avg:.0f}%, "
            f"{len(hygiene)} tâche(s) d'hygiène tracée(s), {due} tâche(s) à faire aujourd'hui."
        ),
    )
