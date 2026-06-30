"""Connecteurs par commerce (modèle B) : enregistrement chiffré + résolution.

Sépare les champs **non sensibles** (stockés en clair) des **secrets** (chiffrés).
`get_credentials` rend la config fusionnée (déchiffrée) pour la fabrique de clients ;
`status` ne renvoie JAMAIS de secret (juste « configuré » + champs publics).
"""

from __future__ import annotations

import contextlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt, encrypt
from app.models.connector import TenantConnector

# Champs par type de connecteur : publics (clair) vs secrets (chiffrés).
PUBLIC_FIELDS: dict[str, list[str]] = {
    "whatsapp": ["phone_number_id", "verify_token"],
    "slack": [],
    "telegram": [],
}
SECRET_FIELDS: dict[str, list[str]] = {
    "whatsapp": ["access_token", "app_secret"],
    "slack": ["bot_token"],
    "telegram": ["bot_token"],
}
# Champs minimaux requis pour considérer le connecteur « configuré » (prêt).
REQUIRED: dict[str, list[str]] = {
    "whatsapp": ["access_token", "phone_number_id"],
    "slack": ["bot_token"],
    "telegram": ["bot_token"],
}

KINDS = list(PUBLIC_FIELDS.keys())


async def _get(session: AsyncSession, kind: str) -> TenantConnector | None:
    return (
        await session.scalars(select(TenantConnector).where(TenantConnector.kind == kind))
    ).first()


async def get_credentials(session: AsyncSession, kind: str) -> dict | None:
    """Config fusionnée (publics + secrets déchiffrés) si le connecteur est actif."""
    row = await _get(session, kind)
    if row is None or not row.active:
        return None
    data: dict = json.loads(row.config or "{}")
    if row.secret_enc:
        # secret illisible (clé changée) → on ignore les secrets
        with contextlib.suppress(Exception):
            data.update(json.loads(decrypt(row.secret_enc)))
    return data


async def upsert(session: AsyncSession, kind: str, fields: dict) -> TenantConnector:
    """Crée/maj un connecteur. Les secrets non fournis sont **conservés** (maj partielle)."""
    if kind not in KINDS:
        raise ValueError(f"Connecteur inconnu : {kind}")
    row = await _get(session, kind)
    if row is None:
        row = TenantConnector(kind=kind, config="{}", secret_enc=None, active=True)
        session.add(row)

    public = {k: fields[k] for k in PUBLIC_FIELDS[kind] if fields.get(k) is not None}
    row.config = json.dumps(public, ensure_ascii=False)

    # Secrets : on repart des secrets existants et on écrase seulement ceux fournis.
    existing: dict = {}
    if row.secret_enc:
        try:
            existing = json.loads(decrypt(row.secret_enc))
        except Exception:
            existing = {}
    for k in SECRET_FIELDS[kind]:
        val = fields.get(k)
        if val:  # non vide → mise à jour ; vide/absent → on garde l'ancien
            existing[k] = val
    row.secret_enc = encrypt(json.dumps(existing, ensure_ascii=False)) if existing else None
    row.active = bool(fields.get("active", True))
    await session.flush()
    return row


async def delete(session: AsyncSession, kind: str) -> bool:
    row = await _get(session, kind)
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True


async def status(session: AsyncSession) -> list[dict]:
    """État par type — **sans secret** : configuré ? actif ? champs publics ?"""
    rows = {r.kind: r for r in (await session.scalars(select(TenantConnector))).all()}
    out: list[dict] = []
    for kind in KINDS:
        row = rows.get(kind)
        creds = {}
        public: dict = {}
        has_secret = False
        if row is not None:
            public = json.loads(row.config or "{}")
            if row.secret_enc:
                has_secret = True
                try:
                    creds = json.loads(decrypt(row.secret_enc))
                except Exception:
                    creds = {}
        configured = all((public.get(f) or creds.get(f)) for f in REQUIRED[kind])
        out.append(
            {
                "kind": kind,
                "configured": bool(configured),
                "active": bool(row.active) if row else False,
                "public": public,  # jamais de secret ici
                "has_secret": has_secret,
            }
        )
    return out
