"""Modèles SQLAlchemy. Importer ce package enregistre toutes les tables sur
`Base.metadata` (requis par Alembic et la création de schéma en test)."""

from app.db.base import Base
from app.models.audit_log import AuditLog
from app.models.event import Event
from app.models.invoice import Invoice, InvoiceLine
from app.models.order import Order, OrderLine
from app.models.product import Product
from app.models.sale import Sale
from app.models.stock import Stock
from app.models.supplier import Supplier
from app.models.user import Role, User

__all__ = [
    "Base",
    "AuditLog",
    "Event",
    "Invoice",
    "InvoiceLine",
    "Order",
    "OrderLine",
    "Product",
    "Sale",
    "Stock",
    "Supplier",
    "Role",
    "User",
]
