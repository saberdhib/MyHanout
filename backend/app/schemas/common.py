"""Schémas communs (réponses paginées, statut)."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "myhanout-api"
    version: str


class ListResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
