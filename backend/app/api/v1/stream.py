"""Endpoint temps réel (SSE) : pushs serveur→client, filtrés par tenant.

Un commerce ne reçoit QUE ses propres events (le tenant vient du token, jamais du
client). Le front s'abonne et met à jour son state ; en cas de coupure, il retombe
sur un polling léger.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.deps import get_current_user
from app.core.events import event_stream
from app.core.exceptions import AuthError
from app.core.security import CurrentUser

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get("/events")
async def events(user: CurrentUser = Depends(get_current_user)) -> StreamingResponse:
    """Flux SSE des événements de l'organisation courante."""
    if user.organization_id is None:
        raise AuthError("Aucune organisation active")
    return StreamingResponse(
        event_stream(user.organization_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
