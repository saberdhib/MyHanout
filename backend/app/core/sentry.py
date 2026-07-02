"""Centralisation des erreurs (Sentry) — activation soft, sans dépendance dure.

Aucune clé/DSN → no-op (parcours mock/keyless intact). `sentry-sdk` non installé mais
DSN fourni → on log un avertissement et on continue. Cohérent avec la règle « provider
mockable par défaut » : Sentry est optionnel, activé par `SENTRY_DSN` + le SDK installé.
"""

from __future__ import annotations

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


def setup_sentry() -> None:
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk
    except ImportError:  # pragma: no cover - dépend d'une install optionnelle
        log.warning("sentry.unavailable", reason="sentry-sdk non installé (pip install sentry-sdk)")
        return
    sentry_sdk.init(  # pragma: no cover - nécessite un DSN réel
        dsn=settings.sentry_dsn,
        environment=settings.env,
        traces_sample_rate=0.0,  # traces via OTEL ; Sentry = erreurs.
    )
    log.info("sentry.enabled", env=settings.env)
