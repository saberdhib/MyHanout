"""Bus d'événements temps réel **in-process**, filtré par tenant (Brique 3).

Le dashboard s'abonne via SSE (`GET /stream/events`) et reçoit les pushs de son
**organisation uniquement** : un commerce ne voit jamais les events d'un autre
(le garde-fou s'applique au niveau du flux). Pas de dépendance externe : un
pub/sub mémoire suffit pour un process API ; en multi-process on brancherait Redis
pub/sub derrière la même interface.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections import defaultdict
from collections.abc import AsyncIterator

from pydantic import BaseModel


class StreamEvent(BaseModel):
    type: str  # ex. inventory_updated | forecast_ready | alert_created | pipeline_finished
    payload: dict = {}


class _Broker:
    """Pub/sub mémoire : une file par abonné, indexée par organisation."""

    def __init__(self) -> None:
        self._subs: dict[int, set[asyncio.Queue]] = defaultdict(set)

    def subscribe(self, org_id: int) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subs[org_id].add(q)
        return q

    def unsubscribe(self, org_id: int, q: asyncio.Queue) -> None:
        self._subs[org_id].discard(q)
        if not self._subs[org_id]:
            self._subs.pop(org_id, None)

    def publish(self, org_id: int, event: StreamEvent) -> None:
        """Diffuse un event aux seuls abonnés de l'organisation (best-effort)."""
        for q in list(self._subs.get(org_id, ())):
            # Abonné lent (file pleine) : on saute l'event (le polling rattrape).
            with contextlib.suppress(asyncio.QueueFull):
                q.put_nowait(event)

    def subscriber_count(self, org_id: int) -> int:
        return len(self._subs.get(org_id, ()))


broker = _Broker()


def publish_event(org_id: int | None, type_: str, payload: dict | None = None) -> None:
    """Helper sûr : publie si une organisation est connue (sinon no-op)."""
    if org_id is None:
        return
    broker.publish(org_id, StreamEvent(type=type_, payload=payload or {}))


async def event_stream(org_id: int, *, heartbeat: float = 15.0) -> AsyncIterator[str]:
    """Générateur SSE : événements de l'org + heartbeat de maintien de connexion."""
    q = broker.subscribe(org_id)
    try:
        # Ping initial pour ouvrir le flux côté client.
        yield ": connected\n\n"
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=heartbeat)
                yield f"event: {event.type}\ndata: {event.model_dump_json()}\n\n"
            except TimeoutError:
                yield ": ping\n\n"
    finally:
        broker.unsubscribe(org_id, q)
