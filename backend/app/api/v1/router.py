"""Agrégateur des routers de l'API v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    agents,
    auth,
    chat,
    customers,
    daily_entries,
    forecasts,
    imports,
    invoices,
    mlops,
    onboarding,
    orders,
    promos,
    rag,
    signals,
    stocks,
    telegram,
    whatsapp,
)

api_router = APIRouter()
api_router.include_router(auth.router)
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
api_router.include_router(forecasts.router)
api_router.include_router(orders.router)
api_router.include_router(daily_entries.router)
api_router.include_router(mlops.router)
api_router.include_router(whatsapp.router)
api_router.include_router(telegram.router)
