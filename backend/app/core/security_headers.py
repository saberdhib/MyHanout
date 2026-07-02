"""Middleware d'en-têtes de sécurité HTTP (durcissement navigateur).

Pose les en-têtes défensifs standards sur chaque réponse : anti-clickjacking,
anti-sniffing MIME, politique de référent, permissions, et HSTS en production.
La CSP reste volontairement permissive (API + dashboard SPA) mais bloque l'embed.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for key, value in _HEADERS.items():
            response.headers.setdefault(key, value)
        # HSTS uniquement hors local (évite d'épingler https en dev).
        if settings.env.lower() != "local":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        return response
