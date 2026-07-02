"""Tableau d'impact (ROI en euros) — consolide la valeur DÉJÀ produite par l'outil.

Un commerçant ne paie pas pour des dashboards, il paie pour un chiffre en euros crédible.
Ce service agrège, sur une période, la valeur concrète que les agents ont générée ou
révélée : gaspillage évité, cash récupéré, trop-payé détecté, démarque inconnue, temps
gagné. Lecture seule, chaque ligne expliquée, estimation assumée (non comptable).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import MarkdownStatus, OrderStatus
from app.models.markdown import MarkdownSuggestion
from app.models.order import Order
from app.models.reservation import Reservation, ReservationStatus
from app.models.sale import Sale
from app.schemas.impact import ImpactLine, ImpactView

# Minutes économisées par décision assistée (réassort validé, démarque appliquée…).
_MINUTES_PER_DECISION = 5


async def compute_impact(session: AsyncSession, *, days: int = 30) -> ImpactView:
    since = datetime.now(UTC) - timedelta(days=days)

    # 1) Démarque appliquée : perte évitée + cash récupéré (sur la période).
    md = (
        await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(MarkdownSuggestion.avoided_loss), 0.0),
                func.coalesce(func.sum(MarkdownSuggestion.recovered_value), 0.0),
            ).where(
                MarkdownSuggestion.status == MarkdownStatus.APPLIED,
                MarkdownSuggestion.updated_at >= since,
            )
        )
    ).one()
    md_count, waste_avoided, cash_recovered = int(md[0]), float(md[1]), float(md[2])

    # 2) Contrôles : trop-payé fournisseur + démarque inconnue (révélés, instantané).
    from app.services.control_service import invoice_controls, shrinkage_report

    overcharge = (await invoice_controls(session)).total_overcharge
    shrinkage = (await shrinkage_report(session)).total_loss

    # 3) Réservations récupérées (CA click & collect sur la période).
    resa = (
        await session.execute(
            select(
                func.count(),
                func.coalesce(func.sum(Reservation.total_amount), 0.0),
            ).where(
                Reservation.status == ReservationStatus.COLLECTED,
                Reservation.updated_at >= since,
            )
        )
    ).one()
    resa_count, resa_revenue = int(resa[0]), float(resa[1])

    # 4) CA de la période (contexte).
    revenue = float(
        await session.scalar(
            select(func.coalesce(func.sum(Sale.total), 0.0)).where(Sale.sold_at >= since)
        )
        or 0
    )

    # 5) Temps gagné : décisions assistées (démarques appliquées + commandes validées).
    orders_confirmed = int(
        await session.scalar(
            select(func.count())
            .select_from(Order)
            .where(
                Order.status.in_([OrderStatus.CONFIRMED, OrderStatus.APPROVED, OrderStatus.SENT]),
                Order.created_at >= since,
            )
        )
        or 0
    )
    decisions = md_count + orders_confirmed + resa_count
    time_saved_hours = round(decisions * _MINUTES_PER_DECISION / 60, 1)

    # Valeur « euros » que l'outil a fait gagner OU révélée.
    estimated_value = round(waste_avoided + cash_recovered + overcharge + shrinkage, 2)

    lines = [
        ImpactLine(
            label="Gaspillage évité (démarque)",
            amount=round(waste_avoided, 2),
            unit="€",
            kind="gain",
            explanation=f"{md_count} démarque(s) appliquée(s) : perte sèche évitée.",
        ),
        ImpactLine(
            label="Cash récupéré (démarque)",
            amount=round(cash_recovered, 2),
            unit="€",
            kind="gain",
            explanation="Chiffre d'affaires récupéré en écoulant plutôt qu'en jetant.",
        ),
        ImpactLine(
            label="Trop-payé fournisseur détecté",
            amount=round(overcharge, 2),
            unit="€",
            kind="detected",
            explanation="Écarts facture vs commande/prix connu (3-way match) — à récupérer.",
        ),
        ImpactLine(
            label="Démarque inconnue détectée",
            amount=round(shrinkage, 2),
            unit="€",
            kind="detected",
            explanation="Pertes invisibles (vol/casse/erreurs) révélées par le contrôle de stock.",
        ),
        ImpactLine(
            label="CA click & collect",
            amount=round(resa_revenue, 2),
            unit="€",
            kind="revenue",
            explanation=f"{resa_count} réservation(s) récupérée(s) sur la période.",
        ),
        ImpactLine(
            label="Temps gagné",
            amount=time_saved_hours,
            unit="h",
            kind="time",
            explanation=(
                f"{decisions} décision(s) assistée(s) × ~{_MINUTES_PER_DECISION} min "
                "(réassort, démarque, réservations)."
            ),
        ),
    ]

    return ImpactView(
        period_days=days,
        currency="EUR",
        estimated_value_eur=estimated_value,
        time_saved_hours=time_saved_hours,
        revenue=round(revenue, 2),
        lines=lines,
        explanation=(
            f"Sur {days} jours : ~{estimated_value:.0f} € gagnés ou révélés par l'outil "
            f"+ ~{time_saved_hours:g} h économisées."
        ),
        disclaimer=(
            "Estimation de pilotage (non comptable), d'après les actions réellement menées."
        ),
    )
