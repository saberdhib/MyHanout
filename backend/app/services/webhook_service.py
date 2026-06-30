"""Webhooks sortants : sélection des endpoints + signature HMAC + livraison HTTP.

Déclenché sur les événements métier (alerte, reco prête, run terminé…). Chaque
livraison est signée (`X-MyHanout-Signature: sha256=<hmac>`). Tolérant aux pannes :
une URL qui échoue n'interrompt jamais le flux métier (best-effort + compteur).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.webhook import WebhookEndpoint

log = get_logger(__name__)


def sign(secret: str, body: bytes) -> str:
    """Signature HMAC-SHA256 hex du corps (à vérifier côté récepteur)."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def new_secret() -> str:
    return secrets.token_hex(24)


def _subscribed(events_csv: str, event: str) -> bool:
    if events_csv.strip() == "*":
        return True
    return event in {e.strip() for e in events_csv.split(",") if e.strip()}


async def deliver(
    session: AsyncSession,
    org_id: int | None,
    event: str,
    payload: dict,
    *,
    client=None,
) -> int:
    """POSTe l'événement aux endpoints actifs de l'org abonnés. Retourne le nb livré.

    `org_id` est filtré EXPLICITEMENT (on peut être hors contexte tenant) — le
    garde-fou ORM ne couvre que les SELECT, et on veut être certain de l'isolation.
    """
    if org_id is None:
        return 0
    endpoints = list(
        (
            await session.scalars(
                select(WebhookEndpoint).where(
                    WebhookEndpoint.organization_id == org_id,
                    WebhookEndpoint.active.is_(True),
                )
            )
        ).all()
    )
    targets = [e for e in endpoints if _subscribed(e.events, event)]
    if not targets:
        return 0

    body = json.dumps({"event": event, "data": payload}, ensure_ascii=False).encode()
    owns = client is None
    if owns:  # pragma: no cover - réseau (tests injectent un client mock)
        import httpx

        client = httpx.AsyncClient(timeout=10)
    delivered = 0
    try:
        for ep in targets:
            headers = {
                "Content-Type": "application/json",
                "X-MyHanout-Event": event,
                "X-MyHanout-Signature": f"sha256={sign(ep.secret, body)}",
            }
            try:
                resp = await client.post(ep.url, content=body, headers=headers)
                ep.last_status = resp.status_code
                ep.last_delivered_at = datetime.now(UTC)
                if resp.status_code >= 400:
                    ep.failures += 1
                else:
                    delivered += 1
            except Exception as exc:  # une URL morte ne casse pas le métier
                ep.failures += 1
                log.warning("webhook.deliver.fail", url=ep.url, error=str(exc))
    finally:
        if owns:  # pragma: no cover
            await client.aclose()
    await session.flush()
    log.info("webhook.deliver", evt=event, targets=len(targets), delivered=delivered)
    return delivered
