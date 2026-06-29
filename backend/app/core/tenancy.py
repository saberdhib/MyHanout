"""Garde-fou central multi-tenant (sécurité, pas convention).

- Un ContextVar `current_org_id` porte l'organisation courante, alimentée
  UNIQUEMENT depuis le token (cf. core.deps), jamais par le client.
- Un event `do_orm_execute` applique `with_loader_criteria` à TOUS les SELECT ORM
  des modèles `TenantMixin` : impossible de lire une autre org, même via
  `session.get`, jointures ou relations.
- Un event `before_flush` estampille `organization_id` sur les INSERT.

Limite connue : les requêtes SQL brutes (hors ORM) ne sont pas filtrées — à
éviter sur les tables tenant (documenté).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

from app.models.tenant import TenantMixin

_current_org_id: ContextVar[int | None] = ContextVar("current_org_id", default=None)


def set_current_org(org_id: int | None) -> object:
    """Définit l'organisation courante. Retourne un token de reset."""
    return _current_org_id.set(org_id)


def reset_current_org(token: object) -> None:
    _current_org_id.reset(token)  # type: ignore[arg-type]


def get_current_org() -> int | None:
    return _current_org_id.get()


@contextmanager
def tenant_context(org_id: int | None) -> Iterator[None]:
    """Force l'organisation courante sur un bloc (workers, seed, tests)."""
    token = _current_org_id.set(org_id)
    try:
        yield
    finally:
        _current_org_id.reset(token)


@event.listens_for(Session, "do_orm_execute")
def _apply_tenant_filter(execute_state) -> None:
    """Filtre automatiquement les SELECT par organisation courante."""
    if not execute_state.is_select:
        return
    if execute_state.is_column_load or execute_state.is_relationship_load:
        return
    org_id = _current_org_id.get()
    if org_id is None:
        return
    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            TenantMixin,
            lambda cls: cls.organization_id == org_id,
            include_aliases=True,
        )
    )


@event.listens_for(Session, "before_flush")
def _stamp_org_on_insert(session: Session, flush_context, instances) -> None:
    """Estampille organization_id sur les nouveaux objets tenant."""
    org_id = _current_org_id.get()
    if org_id is None:
        return
    for obj in session.new:
        if isinstance(obj, TenantMixin) and getattr(obj, "organization_id", None) is None:
            obj.organization_id = org_id
