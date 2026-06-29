"""Équipements suivis (chaîne du froid + machines) et relevés de température.

Suivi HACCP/anti-gaspillage : un frigo qui dérive = perte de marchandise. Les
thermomètres connectés sont une **intégration optionnelle** ; sans capteur, le
provider mock fournit des relevés (keyless). Tout est tenant-scopé.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.base import EquipmentKind
from app.models.tenant import TenantMixin

if TYPE_CHECKING:
    pass


def _kind_col():
    return Enum(EquipmentKind, native_enum=False, values_callable=lambda e: [m.value for m in e])


class Equipment(Base, TenantMixin, TimestampMixin):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    kind: Mapped[EquipmentKind] = mapped_column(_kind_col(), default=EquipmentKind.FRIDGE)
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Plage de température acceptable (°C). Défaut frigo positif.
    min_temp_c: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    max_temp_c: Mapped[float] = mapped_column(Numeric(5, 2), default=4)
    # Identifiant du capteur côté fournisseur (mock/HTTP/MQTT) — optionnel.
    sensor_external_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    readings: Mapped[list[TemperatureReading]] = relationship(
        back_populates="equipment", cascade="all, delete-orphan"
    )


class TemperatureReading(Base, TenantMixin, TimestampMixin):
    __tablename__ = "temperature_reading"

    id: Mapped[int] = mapped_column(primary_key=True)
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE"), index=True
    )
    temp_c: Mapped[float] = mapped_column(Numeric(5, 2))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    # Origine du relevé : mock | http | mqtt | manual.
    source: Mapped[str] = mapped_column(String(32), default="mock")

    equipment: Mapped[Equipment] = relationship(back_populates="readings")
