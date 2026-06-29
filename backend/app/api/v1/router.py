"""Agrégateur des routers de l'API v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    daily_entries,
    forecasts,
    invoices,
    mlops,
    orders,
    stocks,
    whatsapp,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(stocks.router)
api_router.include_router(invoices.router)
api_router.include_router(forecasts.router)
api_router.include_router(orders.router)
api_router.include_router(daily_entries.router)
api_router.include_router(mlops.router)
api_router.include_router(whatsapp.router)
