"""Registre des agents IA."""

from app.intelligence.agents.agent_briefing import BriefingAgent
from app.intelligence.agents.agent_finance import FinanceAgent
from app.intelligence.agents.agent_governance import GovernanceAgent
from app.intelligence.agents.agent_markdown import MarkdownAgent
from app.intelligence.agents.agent_marketing import MarketingAgent
from app.intelligence.agents.agent_order import OrderAgent
from app.intelligence.agents.agent_pricing import PricingAgent
from app.intelligence.agents.agent_production import ProductionAgent
from app.intelligence.agents.agent_report import ReportAgent
from app.intelligence.agents.agent_staffing import StaffingAgent
from app.intelligence.agents.agent_stock import StockAgent
from app.intelligence.agents.agent_support import SupportAgent
from app.intelligence.agents.base_agent import (
    AgentAction,
    AgentContext,
    AgentResult,
    BaseAgent,
)

# Agents disponibles, dans l'ordre de priorité de routage.
AGENT_CLASSES: list[type[BaseAgent]] = [
    OrderAgent,
    StockAgent,
    MarkdownAgent,
    ProductionAgent,
    PricingAgent,
    StaffingAgent,
    ReportAgent,
    BriefingAgent,
    FinanceAgent,
    MarketingAgent,
    GovernanceAgent,
    SupportAgent,  # fallback en dernier
]

__all__ = [
    "AgentAction",
    "AgentContext",
    "AgentResult",
    "BaseAgent",
    "BriefingAgent",
    "FinanceAgent",
    "GovernanceAgent",
    "MarkdownAgent",
    "MarketingAgent",
    "OrderAgent",
    "PricingAgent",
    "ProductionAgent",
    "ReportAgent",
    "StaffingAgent",
    "StockAgent",
    "SupportAgent",
    "AGENT_CLASSES",
]
