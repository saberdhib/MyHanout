"""Résolution des clients de messagerie **par commerce** (modèle B).

Lit d'abord la config du tenant courant (`connector_service`), sinon retombe sur
la fabrique globale (`.env` → mock). Ainsi chaque commerce peut brancher SON
WhatsApp/Slack/Telegram sans toucher au serveur.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.messaging.slack import SlackClient, get_slack_client
from app.messaging.telegram import TelegramClient, get_telegram_client
from app.messaging.whatsapp import WhatsAppClient, get_whatsapp_client
from app.services.connector_service import get_credentials


async def resolve_whatsapp_client(session: AsyncSession) -> WhatsAppClient:
    creds = await get_credentials(session, "whatsapp")
    if creds and creds.get("access_token") and creds.get("phone_number_id"):
        from app.messaging.whatsapp.business_api import BusinessWhatsAppClient

        return BusinessWhatsAppClient(
            token=creds["access_token"], phone_id=creds["phone_number_id"]
        )
    return get_whatsapp_client()


async def resolve_slack_client(session: AsyncSession) -> SlackClient:
    creds = await get_credentials(session, "slack")
    if creds and creds.get("bot_token"):
        from app.messaging.slack import BotSlackClient

        return BotSlackClient(token=creds["bot_token"])
    return get_slack_client()


async def resolve_telegram_client(session: AsyncSession) -> TelegramClient:
    creds = await get_credentials(session, "telegram")
    if creds and creds.get("bot_token"):
        from app.messaging.telegram import BotTelegramClient

        return BotTelegramClient(token=creds["bot_token"])
    return get_telegram_client()
