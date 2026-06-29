"""Machine à états de conversation WhatsApp (persistée).

Parcours type :
  "commande demain"          -> proposition explicable + état AWAITING_CONFIRMATION
  "boeuf 10" / "10"          -> ajustement d'une ligne (reste en attente)
  "oui"                      -> validation -> commande confirmée
  "non"                      -> annulation
  "stock <sku> <restant> <commande>" -> saisie de fin de journée
  photo de facture           -> pipeline OCR (Phase 1)
Tout autre message -> fallback orchestrateur d'agents.
"""

from __future__ import annotations

import json
import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.base import DailyEntrySource
from app.models.conversation import Conversation
from app.models.product import Product
from app.schemas.order import AdjustedLine
from app.services.daily_entry_service import upsert_daily_entry
from app.services.order_action_service import confirm_suggestion
from app.services.suggestion_service import suggest_orders

log = get_logger(__name__)

STATE_IDLE = "idle"
STATE_AWAITING = "awaiting_order_confirmation"

_YES = {"oui", "ok", "valide", "valider", "confirme", "confirmer", "yes"}
_NO = {"non", "annule", "annuler", "stop", "no"}
_ORDER_INTENT = ("command", "réassort", "reassort", "demain", "semaine")


async def _get_conversation(session: AsyncSession, phone: str) -> Conversation:
    conv = await session.scalar(select(Conversation).where(Conversation.phone == phone))
    if conv is None:
        conv = Conversation(phone=phone, state=STATE_IDLE)
        session.add(conv)
        await session.flush()
    return conv


def _format_proposal(lines: list[dict]) -> str:
    body = "\n".join(
        f"• {line['quantity']:g} × {line['product_name']} — {line['explanation']}" for line in lines
    )
    return (
        "Proposition de commande :\n"
        f"{body}\n\n"
        "Répondez *OUI* pour valider, *NON* pour annuler, "
        "ou ajustez (ex : « boeuf 10 »)."
    )


async def _start_order_flow(session: AsyncSession, conv: Conversation, text: str) -> str:
    horizon = "demain" if "demain" in text else ("semaine" if "semaine" in text else None)
    suggestion = await suggest_orders(session, horizon=horizon)
    if not suggestion.lines:
        return "Aucune commande à proposer pour le moment (stocks suffisants)."
    lines = [
        {
            "product_id": line.product_id,
            "product_name": line.product_name,
            "quantity": line.suggested_quantity,
            "explanation": line.explanation,
        }
        for line in suggestion.lines
    ]
    conv.state = STATE_AWAITING
    conv.context = json.dumps({"lines": lines})
    return _format_proposal(lines)


def _apply_adjustment(lines: list[dict], text: str) -> bool:
    """Ajuste une quantité depuis un message libre. True si une ligne a changé."""
    numbers = re.findall(r"\d+(?:[.,]\d+)?", text)
    if not numbers:
        return False
    qty = float(numbers[-1].replace(",", "."))
    lowered = text.lower()
    # Cible par nom de produit si mentionné, sinon la seule ligne disponible.
    for line in lines:
        name = (line["product_name"] or "").lower()
        if name and any(tok in lowered for tok in name.split()):
            line["quantity"] = qty
            return True
    if len(lines) == 1:
        lines[0]["quantity"] = qty
        return True
    return False


async def _confirm_flow(session: AsyncSession, conv: Conversation) -> str:
    ctx = json.loads(conv.context or "{}")
    lines = ctx.get("lines", [])
    order = await confirm_suggestion(
        session,
        user_id=None,
        lines=[
            AdjustedLine(product_id=line["product_id"], quantity=line["quantity"]) for line in lines
        ],
    )
    conv.state = STATE_IDLE
    conv.context = None
    return (
        f"✅ Commande #{order.id} confirmée (mode : {order.action_mode}).\n\n"
        f"{order.supplier_message}"
    )


async def _handle_stock_entry(session: AsyncSession, text: str) -> str | None:
    """Format : 'stock <sku> <restant> <commande?>' -> saisie de fin de journée."""
    m = re.match(
        r"stock\s+([\w-]+)\s+(\d+(?:[.,]\d+)?)(?:\s+(\d+(?:[.,]\d+)?))?",
        text.strip(),
        re.IGNORECASE,
    )
    if not m:
        return None
    sku, remaining, ordered = m.group(1), m.group(2), m.group(3)
    product = await session.scalar(select(Product).where(Product.sku == sku.upper()))
    if not product:
        return f"Produit « {sku} » introuvable. Vérifiez le code."
    await upsert_daily_entry(
        session,
        product_id=product.id,
        entry_date=date.today(),
        quantity_ordered=float((ordered or "0").replace(",", ".")),
        stock_remaining=float(remaining.replace(",", ".")),
        source=DailyEntrySource.WHATSAPP,
    )
    return f"📝 Saisie enregistrée pour {product.name} (reste {remaining})."


async def handle_text(session: AsyncSession, phone: str, text: str) -> str:
    """Point d'entrée texte : pilote la machine à états et renvoie la réponse."""
    conv = await _get_conversation(session, phone)
    lowered = text.strip().lower()
    log.info("conversation.text", phone=phone, state=conv.state)

    if conv.state == STATE_AWAITING:
        if lowered in _YES:
            return await _confirm_flow(session, conv)
        if lowered in _NO:
            conv.state = STATE_IDLE
            conv.context = None
            return "Commande annulée."
        ctx = json.loads(conv.context or "{}")
        lines = ctx.get("lines", [])
        if _apply_adjustment(lines, text):
            conv.context = json.dumps({"lines": lines})
            return _format_proposal(lines)
        return "Je n'ai pas compris l'ajustement. Répondez *OUI*, *NON*, ou « produit qté »."

    # État idle.
    stock_reply = await _handle_stock_entry(session, text)
    if stock_reply is not None:
        return stock_reply
    if any(k in lowered for k in _ORDER_INTENT):
        return await _start_order_flow(session, conv, lowered)

    # Fallback : orchestrateur d'agents (Q&A métier).
    from app.intelligence.llm.orchestrator import get_orchestrator

    result = await get_orchestrator().handle(text)
    return result.reply


async def handle_image(session: AsyncSession, phone: str, media_id: str) -> str:
    """Une photo de facture -> téléchargement + pipeline OCR (Phase 1)."""
    from app.messaging.whatsapp import get_whatsapp_client
    from app.services.invoice_service import ingest_and_store

    client = get_whatsapp_client()
    content = await client.download_media(media_id)
    invoice, reasons = await ingest_and_store(
        session, content, content_type="image/jpeg", filename=f"whatsapp-{media_id}.jpg"
    )
    why = " ".join(reasons[:2])
    return f"📄 Facture reçue (#{invoice.id}), en attente de validation.\n" f"Raison : {why}"
