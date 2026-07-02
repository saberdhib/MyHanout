"""Moteur d'alertes décisionnelles : règles lisibles → alertes auditables.

Chaque règle est explicite (seuil + valeur observée + action recommandée) et
idempotente (pas de doublon tant qu'une alerte de même type/entité est ouverte).
Résolution = action humaine (human-in-the-loop), auditée + poussée en temps réel.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import publish_event
from app.core.tenancy import get_current_org
from app.models.alert import Alert
from app.models.base import AlertKind, AlertPriority, AlertStatus
from app.repositories.stock import StockRepository


async def _open_exists(session: AsyncSession, kind: AlertKind, entity_id: int | None) -> bool:
    found = await session.scalar(
        select(Alert.id).where(
            Alert.kind == kind,
            Alert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]),
            Alert.entity_id == entity_id,
        )
    )
    return found is not None


async def scan_alerts(
    session: AsyncSession,
    *,
    pipeline_run_id: int | None = None,
    today: date | None = None,
    expiring_within_days: int = 7,
) -> list[Alert]:
    """Applique les règles et crée les alertes manquantes (idempotent)."""
    today = today or date.today()
    stock_repo = StockRepository(session)
    created: list[Alert] = []

    # Règle 1 — risque de rupture : stock sous le seuil de réassort.
    for s in await stock_repo.list_low_stock():
        if await _open_exists(session, AlertKind.STOCK_OUT, s.product_id):
            continue
        name = s.product.name if s.product else f"produit #{s.product_id}"
        created.append(
            Alert(
                kind=AlertKind.STOCK_OUT,
                priority=AlertPriority.HIGH,
                title=f"Risque de rupture : {name}",
                message=f"Stock {float(s.quantity):.0f} ≤ seuil {float(s.reorder_threshold):.0f}.",
                rule="stock <= reorder_threshold",
                threshold=float(s.reorder_threshold),
                observed_value=float(s.quantity),
                recommended_action="Lancer une suggestion de commande pour ce produit.",
                explanation="Le stock est passé sous le seuil de réassort configuré.",
                entity_type="product",
                entity_id=s.product_id,
                pipeline_run_id=pipeline_run_id,
            )
        )

    # Règle 2 — péremption proche (produits périssables).
    for s in await stock_repo.list_expiring(within_days=expiring_within_days):
        if await _open_exists(session, AlertKind.EXPIRY, s.product_id):
            continue
        name = s.product.name if s.product else f"produit #{s.product_id}"
        days_left = (s.expiry_date - today).days if s.expiry_date else 0
        critical = days_left <= 2
        created.append(
            Alert(
                kind=AlertKind.EXPIRY,
                priority=AlertPriority.CRITICAL if critical else AlertPriority.HIGH,
                title=f"Péremption proche : {name}",
                message=f"Expire dans {days_left} j (le {s.expiry_date}).",
                rule=f"expiry_date <= today + {expiring_within_days}j",
                threshold=float(expiring_within_days),
                observed_value=float(days_left),
                recommended_action="Créer une promo anti-gaspillage (fin de vie).",
                explanation="Produit périssable proche de la date de péremption.",
                entity_type="product",
                entity_id=s.product_id,
                pipeline_run_id=pipeline_run_id,
            )
        )

    # Règle 3 — dérive de précision : MAPE d'un produit au-dessus du seuil configuré.
    from app.config import settings
    from app.services.mlops_service import aggregate_metrics

    for row in await aggregate_metrics(session):
        mape = row["mape"]
        pid = row["product_id"]
        if mape is None or mape <= settings.mlops_drift_mape_threshold:
            continue
        if await _open_exists(session, AlertKind.FORECAST_DRIFT, pid):
            continue
        seuil = settings.mlops_drift_mape_threshold
        created.append(
            Alert(
                kind=AlertKind.FORECAST_DRIFT,
                priority=AlertPriority.MEDIUM,
                title=f"Dérive de prévision : produit #{pid}",
                message=f"MAPE {mape:.0%} au-dessus du seuil {seuil:.0%}.",
                rule="mape > mlops_drift_mape_threshold",
                threshold=float(settings.mlops_drift_mape_threshold),
                observed_value=float(mape),
                recommended_action="Réentraîner le modèle de ce produit.",
                explanation="La précision des prévisions s'est dégradée (dérive détectée).",
                entity_type="product",
                entity_id=pid,
                pipeline_run_id=pipeline_run_id,
            )
        )

    if created:
        from app.services import webhook_service

        session.add_all(created)
        await session.flush()
        org_id = get_current_org()
        for a in created:
            payload = {
                "id": a.id,
                "kind": str(a.kind),
                "priority": str(a.priority),
                "title": a.title,
            }
            publish_event(org_id, "alert_created", payload)  # temps réel (SSE)
            await webhook_service.deliver(session, org_id, "alert_created", payload)  # n8n/Make/…
    return created


async def list_alerts(
    session: AsyncSession, *, status: str | None = None, limit: int = 100
) -> list[Alert]:
    stmt = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(Alert.status == status)
    return list((await session.scalars(stmt)).all())


async def resolve_alert(
    session: AsyncSession, alert_id: int, *, user_id: int, note: str | None, dismiss: bool
) -> Alert | None:
    """Résolution humaine (auditée) : resolved | dismissed (faux positif)."""
    alert = await session.get(Alert, alert_id)
    if alert is None:
        return None
    alert.status = AlertStatus.DISMISSED if dismiss else AlertStatus.RESOLVED
    alert.resolved_by_user_id = user_id
    alert.resolved_at = datetime.now(UTC)
    alert.resolution_note = note
    await session.flush()
    publish_event(
        get_current_org(),
        "alert_resolved",
        {"id": alert.id, "status": str(alert.status)},
    )
    return alert


def alert_priority_rank(priority: str) -> int:
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return order.get(priority, 9)


# Fenêtre de fraîcheur par défaut pour les alertes DATA_STALE (heures).
DATA_STALE_HOURS = 36


def is_stale(freshness: datetime | None, *, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    if freshness is None:
        return True
    if freshness.tzinfo is None:
        freshness = freshness.replace(tzinfo=UTC)
    return (now - freshness) > timedelta(hours=DATA_STALE_HOURS)
