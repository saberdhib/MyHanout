"""Configuration par client : modules actifs selon le type de commerce (vertical).

Permet au frontend (et à terme à un panneau admin) d'adapter l'UI au commerce :
même socle, modules activés/désactivés par profil. Lecture seule ici ; la
personnalisation fine (overrides par tenant) viendra par-dessus sans changer le socle.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
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


class ConnectorInfo(BaseModel):
    key: str
    label: str
    category: str  # messaging | data | iot | ai
    provider: str  # mode courant (mock, http, business, bot…)
    status: str  # mock | live | needs_config
    configured: bool  # les identifiants du mode réel sont-ils présents ?
    hint: str  # comment activer (variables d'env), sans jamais exposer de secret


class ConnectorsConfig(BaseModel):
    items: list[ConnectorInfo]
    explanation: str


def _connector(
    key: str,
    label: str,
    category: str,
    provider: str,
    *,
    is_mock: bool,
    configured: bool,
    hint: str,
) -> ConnectorInfo:
    # mock → "mock" ; réel + identifiants → "live" ; réel sans identifiants → "needs_config".
    status = "mock" if is_mock else ("live" if configured else "needs_config")
    return ConnectorInfo(
        key=key,
        label=label,
        category=category,
        provider=provider,
        status=status,
        configured=configured,
        hint=hint,
    )


@router.get("/connectors", response_model=ConnectorsConfig)
async def connectors(_: CurrentUser = Depends(get_current_user)) -> ConnectorsConfig:
    """État des connecteurs (messagerie, data, IoT) — **sans exposer de secret**.

    Le mode réel s'active par variables d'env (cf. `.env` / `docs/DEPLOY.md`) ;
    par défaut tout est en `mock` (keyless). On ne renvoie jamais de jeton, seulement
    un booléen « configuré » et un indice d'activation.
    """
    s = settings
    items = [
        _connector(
            "whatsapp",
            "WhatsApp Business",
            "messaging",
            s.whatsapp_provider,
            is_mock=s.whatsapp_provider.lower() == "mock",
            configured=bool(s.whatsapp_access_token and s.whatsapp_phone_number_id),
            hint="WHATSAPP_PROVIDER=business + WHATSAPP_ACCESS_TOKEN + WHATSAPP_PHONE_NUMBER_ID",
        ),
        _connector(
            "telegram",
            "Telegram",
            "messaging",
            s.telegram_provider,
            is_mock=s.telegram_provider.lower() == "mock",
            configured=bool(s.telegram_bot_token),
            hint="TELEGRAM_PROVIDER=bot + TELEGRAM_BOT_TOKEN",
        ),
        _connector(
            "slack",
            "Slack",
            "messaging",
            s.slack_provider,
            is_mock=s.slack_provider.lower() == "mock",
            configured=bool(s.slack_bot_token),
            hint="SLACK_PROVIDER=bot + SLACK_BOT_TOKEN (xoxb-…)",
        ),
        _connector(
            "email",
            "Email (factures IMAP)",
            "data",
            s.email_provider,
            is_mock=s.email_provider.lower() == "mock",
            configured=bool(s.email_imap_host and s.email_imap_user),
            hint="EMAIL_PROVIDER=imap + EMAIL_IMAP_HOST + EMAIL_IMAP_USER + EMAIL_IMAP_PASSWORD",
        ),
        _connector(
            "dwh",
            "Entrepôt de données (DWH)",
            "data",
            s.dwh_target,
            is_mock=s.dwh_target.lower() == "mock",
            configured=bool(s.dwh_url),
            hint="DWH_TARGET=http + DWH_URL",
        ),
        _connector(
            "pos",
            "Caisse (POS)",
            "data",
            s.pos_connector,
            is_mock=s.pos_connector.lower() == "mock",
            configured=bool(s.pos_url),
            hint="POS_CONNECTOR=http + POS_URL",
        ),
        _connector(
            "sensors",
            "Capteurs température",
            "iot",
            s.sensor_provider,
            is_mock=s.sensor_provider.lower() == "mock",
            configured=bool(s.sensor_http_url),
            hint="SENSOR_PROVIDER=http + SENSOR_HTTP_URL",
        ),
        _connector(
            "signals",
            "Signaux externes (météo…)",
            "data",
            s.signals_provider,
            is_mock=s.signals_provider.lower() == "mock",
            configured=bool(s.signals_http_url),
            hint="SIGNALS_PROVIDER=http + SIGNALS_HTTP_URL",
        ),
        _connector(
            "ml_service",
            "Service ML (forecast)",
            "ai",
            s.forecast_service_client,
            is_mock=s.forecast_service_client.lower() == "inprocess",
            configured=bool(s.ml_service_url),
            hint="FORECAST_SERVICE_CLIENT=http + ML_SERVICE_URL",
        ),
    ]
    return ConnectorsConfig(
        items=items,
        explanation=(
            "Par défaut tout tourne en mock (sans clé). Le mode réel s'active par "
            "variables d'environnement (voir docs/DEPLOY.md). Aucun secret n'est exposé ici."
        ),
    )
