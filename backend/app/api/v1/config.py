"""Configuration par client : modules actifs selon le type de commerce (vertical).

Permet au frontend (et à terme à un panneau admin) d'adapter l'UI au commerce :
même socle, modules activés/désactivés par profil. Lecture seule ici ; la
personnalisation fine (overrides par tenant) viendra par-dessus sans changer le socle.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.modules import MODULES, enabled_modules_for
from app.core.security import CurrentUser
from app.models.organization import Organization

router = APIRouter(prefix="/config", tags=["config"])


class ModuleInfo(BaseModel):
    key: str
    label: str
    enabled: bool


class ModulesConfig(BaseModel):
    business_type: str | None = None
    enabled: list[str]
    modules: list[ModuleInfo]


@router.get("/modules", response_model=ModulesConfig)
async def modules(
    session: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ModulesConfig:
    """Modules actifs pour le commerce courant (selon son type)."""
    business_type = None
    if user.organization_id is not None:
        org = await session.get(Organization, user.organization_id)
        business_type = org.business_type if org else None
    enabled = enabled_modules_for(business_type)
    enabled_set = set(enabled)
    return ModulesConfig(
        business_type=business_type,
        enabled=enabled,
        modules=[ModuleInfo(key=k, label=v, enabled=k in enabled_set) for k, v in MODULES.items()],
    )
