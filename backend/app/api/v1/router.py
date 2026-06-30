"""Agrégateur des routers de l'API v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    agents,
    alerts,
    api_keys,
    auth,
    briefing,
    catalog,
    chat,
    config,
    customers,
    daily_entries,
    equipment,
    finance,
    forecasts,
    imports,
    invoices,
    markdown,
    meat,
    mlops,
    onboarding,
    orders,
    pipelines,
    production,
    promos,
    rag,
    recipes,
    recommendations,
    signals,
    slack,
    stocks,
    stream,
    telegram,
    webhooks,
    whatsapp,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(config.router)
api_router.include_router(onboarding.router)
api_router.include_router(agents.router)
api_router.include_router(rag.router)
api_router.include_router(chat.router)
api_router.include_router(signals.router)
api_router.include_router(promos.router)
api_router.include_router(customers.router)
api_router.include_router(stocks.router)
api_router.include_router(invoices.router)
api_router.include_router(imports.router)
api_router.include_router(finance.router)
api_router.include_router(equipment.router)
api_router.include_router(catalog.router)
api_router.include_router(meat.router)
api_router.include_router(forecasts.router)
api_router.include_router(orders.router)
api_router.include_router(daily_entries.router)
api_router.include_router(mlops.router)
api_router.include_router(pipelines.router)
api_router.include_router(recommendations.router)
api_router.include_router(markdown.router)
api_router.include_router(recipes.router)
api_router.include_router(production.router)
api_router.include_router(briefing.router)
api_router.include_router(alerts.router)
api_router.include_router(stream.router)
api_router.include_router(whatsapp.router)
api_router.include_router(telegram.router)
api_router.include_router(slack.router)
api_router.include_router(api_keys.router)
api_router.include_router(webhooks.router)
