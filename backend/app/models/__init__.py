"""Modèles SQLAlchemy. Importer ce package enregistre toutes les tables sur
`Base.metadata` (requis par Alembic et la création de schéma en test)."""

from app.db.base import Base
from app.models.agent_memory import AgentMemory
from app.models.alert import Alert
from app.models.api_key import ApiKey
from app.models.audit_log import AuditLog
from app.models.briefing import BriefingItem, DailyBriefing
from app.models.connector import TenantConnector
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.daily_entry import DailyEntry
from app.models.equipment import Equipment, TemperatureReading
from app.models.event import Event
from app.models.expense import ExpenseCategory, ExpenseClassificationFeedback
from app.models.external_signal import ExternalSignal
from app.models.forecast_evaluation import ForecastEvaluation
from app.models.haccp import HygieneRecord, HygieneTask
from app.models.inventory import InventorySnapshot
from app.models.invoice import Invoice, InvoiceLine
from app.models.markdown import MarkdownSuggestion
from app.models.meat import MeatCut, MeatLot
from app.models.order import Order, OrderLine
from app.models.organization import Invitation, Membership, MembershipRole, Organization
from app.models.pipeline import PipelineRun
from app.models.pricing import PriceHistory
from app.models.product import Product
from app.models.promo import PromoCampaign
from app.models.recipe import ProductionPlan, Recipe, RecipeItem
from app.models.recommendation import Recommendation
from app.models.sale import Sale
from app.models.signal import SignalDefinition, SignalObservation
from app.models.stock import Stock
from app.models.supplier import Supplier
from app.models.user import Role, User
from app.models.webhook import WebhookEndpoint

__all__ = [
    "Base",
    "AgentMemory",
    "Alert",
    "ApiKey",
    "AuditLog",
    "BriefingItem",
    "Conversation",
    "DailyBriefing",
    "TenantConnector",
    "Customer",
    "DailyEntry",
    "Equipment",
    "Event",
    "ExpenseCategory",
    "ExpenseClassificationFeedback",
    "ExternalSignal",
    "TemperatureReading",
    "ForecastEvaluation",
    "HygieneRecord",
    "HygieneTask",
    "InventorySnapshot",
    "Invitation",
    "Invoice",
    "InvoiceLine",
    "MarkdownSuggestion",
    "MeatCut",
    "MeatLot",
    "Membership",
    "MembershipRole",
    "Order",
    "OrderLine",
    "PipelineRun",
    "PriceHistory",
    "ProductionPlan",
    "Recipe",
    "RecipeItem",
    "Recommendation",
    "SignalDefinition",
    "SignalObservation",
    "Organization",
    "Product",
    "PromoCampaign",
    "Sale",
    "Stock",
    "Supplier",
    "Role",
    "User",
    "WebhookEndpoint",
]
