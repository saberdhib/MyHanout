"""Briefing du matin : l'agent « Tâches du jour » consolide les sorties des autres
agents (alertes, réassort, démarque, production) en une liste d'actions priorisées.

Lecture des sorties **persistées** (produites par le cycle quotidien) :
- alertes ouvertes, recommandations de réassort, démarques suggérées, plans de production.
On rafraîchit au passage la démarque et la production (peu coûteux, sans pipeline).

Persisté en `daily_briefing` + `briefing_item` ; chaque tâche est cochable (human-in-the-loop)
et le briefing peut être poussé sur WhatsApp/Slack.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import get_current_org
from app.messaging.whatsapp import get_whatsapp_client
from app.models.alert import Alert
from app.models.base import (
    AlertStatus,
    BriefingStatus,
    MarkdownStatus,
    ProductionStatus,
    RecommendationStatus,
)
from app.models.briefing import BriefingItem, DailyBriefing
from app.models.markdown import MarkdownSuggestion
from app.models.product import Product
from app.models.recipe import ProductionPlan
from app.models.recommendation import Recommendation
from app.services.markdown_service import compute_markdowns
from app.services.production_service import compute_production


async def _product_names(session: AsyncSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = await session.execute(select(Product.id, Product.name).where(Product.id.in_(ids)))
    return {r[0]: r[1] for r in rows}


def _alert_priority(value: str | None) -> int:
    v = (value or "").lower()
    if "high" in v or "crit" in v or "urgent" in v:
        return 1
    if "low" in v:
        return 3
    return 1  # une alerte ouverte est par défaut prioritaire


async def _gather_items(session: AsyncSession) -> list[dict]:
    items: list[dict] = []

    # 1) Alertes ouvertes (urgent).
    alerts = list(
        (await session.scalars(select(Alert).where(Alert.status == AlertStatus.OPEN))).all()
    )
    for a in alerts:
        items.append(
            {
                "category": "alert",
                "priority": _alert_priority(str(a.priority)),
                "title": a.title,
                "detail": a.explanation or a.message,
                "action": a.recommended_action,
                "value": 0.0,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
            }
        )

    # Pré-charge les noms produits des sources restantes.
    recos = list(
        (
            await session.scalars(
                select(Recommendation)
                .where(
                    Recommendation.status == RecommendationStatus.SUGGESTED,
                    Recommendation.action == "order",
                )
                .order_by(Recommendation.score.desc())
                .limit(10)
            )
        ).all()
    )
    markdowns = list(
        (
            await session.scalars(
                select(MarkdownSuggestion)
                .where(MarkdownSuggestion.status == MarkdownStatus.SUGGESTED)
                .order_by(MarkdownSuggestion.score.desc())
                .limit(10)
            )
        ).all()
    )
    plans = list(
        (
            await session.scalars(
                select(ProductionPlan).where(
                    ProductionPlan.status == ProductionStatus.SUGGESTED,
                    ProductionPlan.suggested_quantity > 0,
                )
            )
        ).all()
    )
    names = await _product_names(
        session,
        {r.product_id for r in recos}
        | {m.product_id for m in markdowns}
        | {p.product_id for p in plans},
    )

    # 2) Réassort.
    for r in recos:
        name = names.get(r.product_id, f"#{r.product_id}")
        items.append(
            {
                "category": "reassort",
                "priority": 2,
                "title": f"Commander {r.suggested_quantity:.0f} · {name}",
                "detail": r.explanation,
                "action": "Valider la commande",
                "value": 0.0,
                "entity_type": "recommendation",
                "entity_id": r.id,
            }
        )

    # 3) Démarques (valeur récupérable).
    for m in markdowns:
        name = names.get(m.product_id, f"#{m.product_id}")
        items.append(
            {
                "category": "markdown",
                "priority": 2,
                "title": f"Démarquer {name} -{m.discount_pct}%",
                "detail": m.explanation,
                "action": f"Appliquer -{m.discount_pct}% (→ {m.suggested_price:.2f}€)",
                "value": float(m.recovered_value),
                "entity_type": "markdown",
                "entity_id": m.id,
            }
        )

    # 4) Production.
    for p in plans:
        name = names.get(p.product_id, f"#{p.product_id}")
        items.append(
            {
                "category": "production",
                "priority": 3,
                "title": f"Produire {p.suggested_quantity:.0f} · {name}",
                "detail": p.explanation,
                "action": "Confirmer la production",
                "value": 0.0,
                "entity_type": "production",
                "entity_id": p.id,
            }
        )

    items.sort(key=lambda it: (it["priority"], -it["value"]))
    return items


def _summary(items: list[dict]) -> tuple[str, float]:
    n_alert = sum(1 for i in items if i["category"] == "alert")
    n_reassort = sum(1 for i in items if i["category"] == "reassort")
    n_markdown = sum(1 for i in items if i["category"] == "markdown")
    n_prod = sum(1 for i in items if i["category"] == "production")
    value = round(sum(i["value"] for i in items), 2)
    parts = []
    if n_alert:
        parts.append(f"{n_alert} alerte(s)")
    if n_reassort:
        parts.append(f"{n_reassort} réassort")
    if n_markdown:
        parts.append(f"{n_markdown} démarque(s) (~{value:.0f}€ récupérables)")
    if n_prod:
        parts.append(f"{n_prod} à produire")
    detail = ", ".join(parts) if parts else "rien d'urgent aujourd'hui"
    return f"{len(items)} action(s) du jour : {detail}.", value


async def compute_briefing(
    session: AsyncSession,
    *,
    persist: bool = False,
    pipeline_run_id: int | None = None,
    today: date | None = None,
    refresh_agents: bool = True,
) -> DailyBriefing:
    """Consolide les sorties des agents en un briefing (optionnellement persisté)."""
    today = today or date.today()
    if refresh_agents:
        # Rafraîchit démarque & production (peu coûteux, sans pipeline complet).
        await compute_markdowns(session, persist=True)
        await compute_production(session, persist=True)

    items = await _gather_items(session)
    summary, total_value = _summary(items)

    briefing = DailyBriefing(
        briefing_date=today,
        pipeline_run_id=pipeline_run_id,
        summary=summary,
        total_items=len(items),
        total_value=total_value,
        status=BriefingStatus.DRAFT,
    )
    for it in items:
        briefing.items.append(BriefingItem(**it))

    if persist:
        # Remplace les brouillons précédents (DELETE ORM → filtrer l'org À LA MAIN).
        org_id = get_current_org()
        if org_id is not None:
            old = list(
                (
                    await session.scalars(
                        select(DailyBriefing).where(
                            DailyBriefing.organization_id == org_id,
                            DailyBriefing.status == BriefingStatus.DRAFT,
                        )
                    )
                ).all()
            )
            for b in old:
                await session.delete(b)
            await session.flush()
        session.add(briefing)
        await session.flush()
    return briefing


async def latest_briefing(session: AsyncSession) -> DailyBriefing | None:
    from sqlalchemy.orm import selectinload

    return (
        await session.scalars(
            select(DailyBriefing)
            .options(selectinload(DailyBriefing.items))
            .order_by(DailyBriefing.id.desc())
            .limit(1)
        )
    ).first()


async def mark_item_done(session: AsyncSession, item_id: int, done: bool = True) -> bool:
    item = await session.get(BriefingItem, item_id)
    if item is None:
        return False
    item.done = done
    await session.flush()
    return True


def format_briefing_text(briefing: DailyBriefing) -> str:
    lines = [f"☀️ Briefing MyHanout — {briefing.briefing_date}", briefing.summary, ""]
    for it in briefing.items[:12]:
        tag = {"alert": "⚠️", "markdown": "🏷️", "reassort": "🛒", "production": "🥖"}.get(
            it.category, "•"
        )
        lines.append(f"{tag} {it.title}")
    return "\n".join(lines)


async def send_briefing(
    session: AsyncSession, briefing_id: int, *, to: str = "demo"
) -> DailyBriefing | None:
    """Pousse le briefing sur WhatsApp (mock par défaut) et marque comme envoyé."""
    from sqlalchemy.orm import selectinload

    briefing = (
        await session.scalars(
            select(DailyBriefing)
            .options(selectinload(DailyBriefing.items))
            .where(DailyBriefing.id == briefing_id)
        )
    ).first()
    if briefing is None:
        return None
    client = get_whatsapp_client()
    await client.send_text(to, format_briefing_text(briefing))
    briefing.status = BriefingStatus.SENT
    await session.flush()
    return briefing
