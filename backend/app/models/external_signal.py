"""Signal externe **propre au commerçant** (différenciateur MyHanout).

À ne pas confondre avec `signal_definition`/`signal_observation` (séries
publiques globales : météo nationale, vacances…). Ici on stocke les signaux
**locaux** que le commerçant connaît mieux que personne : match de foot du
quartier, jour de paie (le 5), braderie, fête religieuse, météo ressentie…

C'est une table **tenant** (chaque commerce a ses propres signaux) ; le moteur
de recommandation les croise avec les séries génériques.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Enum, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.base import SignalKind
from app.models.tenant import TenantMixin


class ExternalSignal(Base, TenantMixin, TimestampMixin):
    __tablename__ = "external_signal"
    # Un signal par (org, clé, date) — l'org est estampillée par le garde-fou.
    __table_args__ = (
        UniqueConstraint("organization_id", "key", "signal_date", name="uq_external_signal"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(48), index=True)  # ex. "match_local", "paie_5"
    label: Mapped[str] = mapped_column(String(128))
    kind: Mapped[SignalKind] = mapped_column(
        Enum(SignalKind, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=SignalKind.CUSTOM,
    )
    signal_date: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[float] = mapped_column(Float, default=1.0)  # intensité (bool encodé 0/1)
    value_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Provenance (merchant | adapter mocké | source future) et portée (store/quartier).
    source: Mapped[str] = mapped_column(String(32), default="merchant")
    scope: Mapped[str | None] = mapped_column(String(32), nullable=True)
