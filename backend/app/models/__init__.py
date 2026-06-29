"""Modèles SQLAlchemy. Importer ce package enregistre toutes les tables sur
`Base.metadata` (requis par Alembic et la création de schéma en test)."""

from app.db.base import Base
from app.models.agent_memory import AgentMemory
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.daily_entry import DailyEntry
from app.models.equipment import Equipment, TemperatureReading
from app.models.event import Event
from app.models.expense import ExpenseCategory, ExpenseClassificationFeedback
from app.models.forecast_evaluation import ForecastEvaluation
from app.models.invoice import Invoice, InvoiceLine
from app.models.order import Order, OrderLine
from app.models.organization import Invitation, Membership, MembershipRole, Organization
from app.models.product import Product
from app.models.promo import PromoCampaign
from app.models.sale import Sale
from app.models.stock import Stock
from app.models.supplier import Supplier
from app.models.user import Role, User

__all__ = [
    "Base",
    "AgentMemory",
    "AuditLog",
    "Conversation",
    "Customer",
    "DailyEntry",
    "Equipment",
    "Event",
    "ExpenseCategory",
    "ExpenseClassificationFeedback",
    "TemperatureReading",
    "ForecastEvaluation",
    "Invitation",
    "Invoice",
    "InvoiceLine",
    "Membership",
    "MembershipRole",
    "Order",
    "OrderLine",
    "Organization",
    "Product",
    "PromoCampaign",
    "Sale",
    "Stock",
    "Supplier",
    "Role",
    "User",
]
