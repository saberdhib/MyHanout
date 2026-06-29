"""Validation d'une suggestion ajustée -> commande + action (3 modes).

Human-in-the-loop strict : aucune commande n'est transmise sans validation
explicite. Trois modes au choix (préférence par fournisseur, surchargeable) :
  - whatsapp_auto : message WhatsApp envoyé au fournisseur (via le provider)
  - draft         : brouillon prêt à copier/coller (rien n'est envoyé)
  - record_only   : enregistrement seul (le commerçant appelle lui-même)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.logging import get_logger
from app.messaging.whatsapp import get_whatsapp_client
from app.models.base import OrderActionMode, OrderStatus
from app.models.order import Order, OrderLine
from app.models.product import Product
from app.models.supplier import Supplier
from app.schemas.order import AdjustedLine

log = get_logger(__name__)


def build_supplier_message(supplier: Supplier | None, lines: list[tuple[Product, float]]) -> str:
    """Construit le message/brouillon de commande destiné au fournisseur."""
    who = supplier.name if supplier else "Fournisseur"
    items = "\n".join(f"- {qty:g} {p.unit} {p.name}" for p, qty in lines)
    return (
        f"Bonjour {who},\n"
        f"Je souhaite commander :\n{items}\n"
        f"Merci de me confirmer la disponibilité et le délai.\n"
        f"— Envoyé via MyHanout AI"
    )


async def confirm_suggestion(
    session: AsyncSession,
    *,
    user_id: int | None,
    lines: list[AdjustedLine],
    supplier_id: int | None = None,
    action_mode: OrderActionMode | None = None,
) -> Order:
    """Crée une commande `confirmed` à partir d'une suggestion ajustée, puis agit."""
    supplier = await session.get(Supplier, supplier_id) if supplier_id else None

    # Mode : surcharge explicite > préférence fournisseur > record_only.
    mode = action_mode or (
        OrderActionMode(supplier.default_order_mode)
        if supplier and supplier.default_order_mode
        else OrderActionMode.RECORD_ONLY
    )

    # Charge les produits pour libellés + prix.
    product_ids = [line.product_id for line in lines]
    products = {
        p.id: p
        for p in (await session.scalars(select(Product).where(Product.id.in_(product_ids)))).all()
    }

    order = Order(
        supplier_id=supplier_id,
        status=OrderStatus.CONFIRMED,
        requires_approval=False,  # déjà validée explicitement par l'humain
        created_by_id=user_id,
        approved_by_id=user_id,
        action_mode=mode,
    )
    total = 0.0
    line_pairs: list[tuple[Product, float]] = []
    for line in lines:
        product = products.get(line.product_id)
        if not product:
            continue
        unit_price = float(product.unit_price or 0)
        total += unit_price * line.quantity
        line_pairs.append((product, line.quantity))
        order.lines.append(
            OrderLine(
                product_id=line.product_id,
                quantity=line.quantity,
                unit_price=unit_price,
            )
        )
    order.total_amount = total

    message = build_supplier_message(supplier, line_pairs)
    order.supplier_message = message
    session.add(order)
    await session.flush()

    # Action selon le mode (jamais d'envoi sans cette validation explicite).
    if mode == OrderActionMode.WHATSAPP_AUTO and supplier and supplier.phone:
        client = get_whatsapp_client()
        await client.send_text(supplier.phone, message)
        order.status = OrderStatus.SENT
        order.sent_at = datetime.now(UTC)
        log.info("order.action.whatsapp_sent", order_id=order.id, to=supplier.phone)
    else:
        # draft / record_only : rien n'est envoyé automatiquement.
        log.info("order.action.no_send", order_id=order.id, mode=mode.value)

    await record_audit(
        session,
        action="order.confirm",
        user_id=user_id,
        resource="order",
        resource_id=order.id,
        detail=json.dumps({"mode": mode.value, "lines": len(line_pairs)}),
    )
    return order
