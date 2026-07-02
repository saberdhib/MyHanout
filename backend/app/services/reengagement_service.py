"""Service relance client : segmentation (fidélité + activité) + envoi ciblé.

RGPD : on ne contacte QUE les clients opt-in (avec téléphone). Human-in-the-loop :
le commerçant visualise les segments puis déclenche l'envoi ; chaque envoi est audité.
Envoi via le résolveur de connecteurs (WhatsApp du commerce, mock par défaut).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.intelligence.reengagement.engine import Segment, classify
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.loyalty import LoyaltyAccount, LoyaltyTransaction
from app.schemas.reengagement import (
    ReengagementCustomer,
    SegmentOut,
    SegmentsResponse,
    SendResult,
)

log = get_logger(__name__)

_DISCLAIMER = "Relance envoyée uniquement aux clients ayant donné leur consentement (opt-in RGPD)."


async def _last_activity_by_customer(session: AsyncSession) -> dict[int, datetime]:
    rows = await session.execute(
        select(LoyaltyTransaction.customer_id, func.max(LoyaltyTransaction.created_at)).group_by(
            LoyaltyTransaction.customer_id
        )
    )
    return {r[0]: r[1] for r in rows if r[1] is not None}


async def _collect(session: AsyncSession) -> dict[str, list[ReengagementCustomer]]:
    """Classe chaque compte fidélité dans son segment (ou aucun)."""
    accounts = list(await session.scalars(select(LoyaltyAccount)))
    customers = {c.id: c for c in await session.scalars(select(Customer))}
    last_activity = await _last_activity_by_customer(session)
    now = datetime.now(UTC)

    buckets: dict[str, list[ReengagementCustomer]] = {s.value: [] for s in Segment}
    for acc in accounts:
        cust = customers.get(acc.customer_id)
        if cust is None:
            continue
        last = last_activity.get(acc.customer_id)
        if last is not None:
            # sqlite stocke des datetimes naïfs ; on les considère en UTC.
            if last.tzinfo is None:
                last = last.replace(tzinfo=UTC)
            days: int | None = (now - last).days
        else:
            days = None
        decision = classify(
            balance=acc.points_balance,
            threshold=settings.loyalty_reward_threshold,
            days_since_last=days,
            reward_label=settings.loyalty_reward_label,
            almost_gap=settings.reengagement_almost_gap,
            inactive_days=settings.reengagement_inactive_days,
        )
        if decision.segment is None:
            continue
        buckets[decision.segment.value].append(
            ReengagementCustomer(
                customer_id=cust.id,
                name=cust.name,
                phone=cust.phone,
                balance=acc.points_balance,
                contactable=bool(cust.consent_opt_in and cust.phone),
            )
        )
    return buckets


def _message_for(segment: str) -> tuple[str, str]:
    """Message + explication représentatifs d'un segment (règle pure, sans client)."""
    decision = classify(
        balance=(
            settings.loyalty_reward_threshold
            if segment == Segment.REWARD_READY.value
            else (
                settings.loyalty_reward_threshold - 1
                if segment == Segment.ALMOST_REWARD.value
                else 0
            )
        ),
        threshold=settings.loyalty_reward_threshold,
        days_since_last=(
            settings.reengagement_inactive_days if segment == Segment.INACTIVE.value else 0
        ),
        reward_label=settings.loyalty_reward_label,
        almost_gap=settings.reengagement_almost_gap,
        inactive_days=settings.reengagement_inactive_days,
    )
    return decision.message, decision.explanation


async def build_segments(session: AsyncSession) -> SegmentsResponse:
    buckets = await _collect(session)
    out: list[SegmentOut] = []
    for seg in Segment:
        people = buckets[seg.value]
        if not people:
            continue
        message, explanation = _message_for(seg.value)
        out.append(
            SegmentOut(
                segment=seg.value,
                message=message,
                explanation=explanation,
                total=len(people),
                contactable=sum(1 for p in people if p.contactable),
                customers=people,
            )
        )
    return SegmentsResponse(segments=out, disclaimer=_DISCLAIMER)


async def send_campaign(session: AsyncSession, segment: str, user_id: int) -> SendResult:
    """Envoie le message de relance aux clients opt-in du segment (via résolveur)."""
    if segment not in {s.value for s in Segment}:
        raise ValueError(f"Segment inconnu : {segment}")
    buckets = await _collect(session)
    people = buckets.get(segment, [])
    message, _ = _message_for(segment)

    from app.messaging.resolver import resolve_whatsapp_client

    client = await resolve_whatsapp_client(session)
    sent = skipped_no_consent = skipped_no_phone = 0
    for p in people:
        if not p.contactable:
            if not p.phone:
                skipped_no_phone += 1
            else:
                skipped_no_consent += 1
            continue
        await client.send_text(p.phone or "", message)
        sent += 1

    session.add(
        AuditLog(
            user_id=user_id,
            action="reengagement.send",
            resource="segment",
            detail=json.dumps(
                {"segment": segment, "sent": sent, "message": message}, ensure_ascii=False
            ),
        )
    )
    await session.commit()
    log.info("reengagement.sent", segment=segment, sent=sent)
    return SendResult(
        segment=segment,
        sent=sent,
        skipped_no_consent=skipped_no_consent,
        skipped_no_phone=skipped_no_phone,
        message=message,
    )
