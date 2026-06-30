"""Signaux externes (météo, vacances, carburant, foot…) pour le forecasting.

Ces signaux sont des **données publiques** (non propres à un commerce) : ils sont
donc **globaux** (PAS `TenantMixin`), comme `expense_category`. On les aligne aux
ventes par date (+ région optionnelle) pour évaluer la corrélation avec la demande.

- `SignalDefinition` : registre des séries disponibles (clé, libellé, type, source).
  C'est ici que l'admin déclare une nouvelle source de données (+ provider/API).
- `SignalObservation` : la valeur d'un signal à une date (la matière à entraîner).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Enum, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.base import SignalKind


def _kind():
    return Enum(SignalKind, native_enum=False, values_callable=lambda e: [m.value for m in e])


class SignalDefinition(Base, TimestampMixin):
    """Registre d'une série de signal (point d'extension : ajouter une source)."""

    __tablename__ = "signal_definition"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(48), unique=True, index=True)  # ex. "weather_temp_c"
    label: Mapped[str] = mapped_column(String(128))
    kind: Mapped[SignalKind] = mapped_column(_kind(), default=SignalKind.CUSTOM)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)  # °C, €/L, bool…
    # Provider qui alimente la série (mock | http | manual) + indice de source.
    provider: Mapped[str] = mapped_column(String(32), default="mock")
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)


class SignalObservation(Base, TimestampMixin):
    """Valeur d'un signal à une date (et région optionnelle)."""

    __tablename__ = "signal_observation"
    __table_args__ = (UniqueConstraint("signal_key", "region", "obs_date", name="uq_signal_obs"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    signal_key: Mapped[str] = mapped_column(String(48), index=True)
    region: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    obs_date: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[float] = mapped_column(Float)  # numérique (bool encodé 0/1)
    value_text: Mapped[str | None] = mapped_column(String(255), nullable=True)  # ex. "OM-PSG"
