"""Service du plan plateforme (backoffice) — pilotage cross-tenant du parc clients.

⚠️ Toutes ces fonctions lisent/écrivent **au travers des commerces** (garde-fou tenant
désactivé par `get_platform_admin`). Les mutations sont **auditées** via `platform_audit`.
Les agrégats sont explicitement lus sous `tenant_context(None)` (robustesse).
"""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.core.tenancy import tenant_context
from app.models.audit_log import AuditLog
from app.models.connector import TenantConnector
from app.models.invoice import Invoice
from app.models.organization import Membership, MembershipRole, Organization, OrgStatus
from app.models.platform import Plan, Subscription, SubscriptionStatus
from app.models.product import Product
from app.models.sale import Sale
from app.models.user import User
from app.schemas.platform import ClientDetail, ClientSummary, PlatformOverview


async def platform_audit(
    session: AsyncSession,
    admin_user_id: int,
    action: str,
    *,
    org_id: int | None = None,
    detail: dict | None = None,
) -> None:
    """Trace une action plateforme (préfixe `platform.`) dans le journal d'audit."""
    session.add(
        AuditLog(
            user_id=admin_user_id,
            action=f"platform.{action}",
            resource="organization",
            resource_id=org_id,
            detail=json.dumps(detail, ensure_ascii=False) if detail else None,
        )
    )


def _count_by_org(rows) -> dict[int, int]:
    """Transforme des lignes (org_id, count) en dict (évite dict(Result))."""
    return {r[0]: r[1] for r in rows}


async def list_clients(session: AsyncSession) -> list[ClientSummary]:
    """Vue 360 (liste) : un résumé par commerce, agrégats cross-tenant."""
    with tenant_context(None):
        orgs = list(await session.scalars(select(Organization).order_by(Organization.name)))
        subs = {s.organization_id: s for s in await session.scalars(select(Subscription))}
        users = _count_by_org(
            await session.execute(
                select(
                    Membership.organization_id, func.count(func.distinct(Membership.user_id))
                ).group_by(Membership.organization_id)
            )
        )
        products = _count_by_org(
            await session.execute(
                select(Product.organization_id, func.count()).group_by(Product.organization_id)
            )
        )
        sales = _count_by_org(
            await session.execute(
                select(Sale.organization_id, func.count()).group_by(Sale.organization_id)
            )
        )

    out: list[ClientSummary] = []
    for org in orgs:
        sub = subs.get(org.id)
        out.append(
            ClientSummary(
                organization_id=org.id,
                name=org.name,
                slug=org.slug,
                business_type=org.business_type,
                status=str(org.status),
                plan=str(sub.plan) if sub else "—",
                subscription_status=str(sub.status) if sub else None,
                mrr_eur=sub.mrr_eur if sub else 0.0,
                users=users.get(org.id, 0),
                products=products.get(org.id, 0),
                sales=sales.get(org.id, 0),
                created_at=org.created_at.isoformat() if org.created_at else None,
            )
        )
    return out


async def overview(session: AsyncSession) -> PlatformOverview:
    """Indicateurs de parc : nombre de clients par statut + MRR/ARR agrégés."""
    with tenant_context(None):
        orgs = list(await session.scalars(select(Organization)))
        subs = list(await session.scalars(select(Subscription)))
    mrr = sum(s.mrr_eur for s in subs if s.status != SubscriptionStatus.CANCELLED)
    by_status = dict.fromkeys(("active", "trial", "suspended", "cancelled"), 0)
    for org in orgs:
        by_status[str(org.status)] = by_status.get(str(org.status), 0) + 1
    return PlatformOverview(
        clients_total=len(orgs),
        clients_active=by_status.get("active", 0),
        clients_trial=by_status.get("trial", 0),
        clients_suspended=by_status.get("suspended", 0),
        mrr_total_eur=round(mrr, 2),
        arr_total_eur=round(mrr * 12, 2),
    )


async def client_detail(session: AsyncSession, org_id: int) -> ClientDetail | None:
    """Fiche détaillée d'un commerce (agrégats + abonnement + connecteurs)."""
    with tenant_context(None):
        org = await session.get(Organization, org_id)
        if org is None:
            return None
        sub = await session.scalar(
            select(Subscription).where(Subscription.organization_id == org_id)
        )
        users = await session.scalar(
            select(func.count(func.distinct(Membership.user_id))).where(
                Membership.organization_id == org_id
            )
        )
        products = await session.scalar(
            select(func.count()).select_from(Product).where(Product.organization_id == org_id)
        )
        sales = await session.scalar(
            select(func.count()).select_from(Sale).where(Sale.organization_id == org_id)
        )
        invoices = await session.scalar(
            select(func.count()).select_from(Invoice).where(Invoice.organization_id == org_id)
        )
        last_sale = await session.scalar(
            select(func.max(Sale.sold_at)).where(Sale.organization_id == org_id)
        )
        connectors = await session.scalar(
            select(func.count())
            .select_from(TenantConnector)
            .where(TenantConnector.organization_id == org_id)
        )

    return ClientDetail(
        organization_id=org.id,
        name=org.name,
        slug=org.slug,
        business_type=org.business_type,
        status=str(org.status),
        plan=str(sub.plan) if sub else "—",
        subscription_status=str(sub.status) if sub else None,
        mrr_eur=sub.mrr_eur if sub else 0.0,
        users=users or 0,
        products=products or 0,
        sales=sales or 0,
        invoices=invoices or 0,
        connectors_configured=connectors or 0,
        open_tickets=0,  # câblé au Lot 3 (support)
        last_sale_at=last_sale.isoformat() if last_sale else None,
        created_at=org.created_at.isoformat() if org.created_at else None,
        trial_ends_on=sub.trial_ends_on if sub else None,
        started_on=sub.started_on if sub else None,
        current_period_end=sub.current_period_end if sub else None,
        notes=sub.notes if sub else None,
    )


async def provision_client(
    session: AsyncSession,
    admin_user_id: int,
    *,
    name: str,
    slug: str,
    business_type: str | None,
    owner_email: str,
    owner_full_name: str | None,
    owner_password: str,
    plan: str,
) -> Organization:
    """Crée un nouveau commerce : organisation + owner + abonnement (audité).

    Idempotence : refuse un slug déjà pris. Réutilise un utilisateur existant par email.
    """
    with tenant_context(None):
        exists = await session.scalar(select(Organization).where(Organization.slug == slug))
        if exists is not None:
            raise ValueError(f"Le slug « {slug} » est déjà utilisé.")

        plan_enum = Plan(plan) if plan in {p.value for p in Plan} else Plan.TRIAL
        org = Organization(
            name=name,
            slug=slug,
            business_type=business_type,
            status=OrgStatus.TRIAL if plan_enum == Plan.TRIAL else OrgStatus.ACTIVE,
        )
        session.add(org)

        owner = await session.scalar(select(User).where(User.email == owner_email))
        if owner is None:
            owner = User(
                email=owner_email,
                full_name=owner_full_name,
                hashed_password=hash_password(owner_password),
            )
            session.add(owner)
        await session.flush()

        session.add(Membership(user_id=owner.id, organization_id=org.id, role=MembershipRole.OWNER))
        today = date.today().isoformat()
        session.add(
            Subscription(
                organization_id=org.id,
                plan=plan_enum,
                status=(
                    SubscriptionStatus.TRIALING
                    if plan_enum == Plan.TRIAL
                    else SubscriptionStatus.ACTIVE
                ),
                started_on=today,
            )
        )
        await platform_audit(
            session,
            admin_user_id,
            "provision_client",
            org_id=org.id,
            detail={"slug": slug, "plan": plan_enum.value, "owner": owner_email},
        )
        await session.commit()
    return org


async def set_org_status(
    session: AsyncSession, admin_user_id: int, org_id: int, status: str, reason: str | None = None
) -> Organization | None:
    """Change le cycle de vie d'un commerce (suspend/réactive). Audité."""
    if status not in {s.value for s in OrgStatus}:
        raise ValueError(f"Statut invalide : {status}")
    with tenant_context(None):
        org = await session.get(Organization, org_id)
        if org is None:
            return None
        old = str(org.status)
        org.status = OrgStatus(status)
        await platform_audit(
            session,
            admin_user_id,
            "set_status",
            org_id=org_id,
            detail={"from": old, "to": status, "reason": reason},
        )
        await session.commit()
    return org


async def set_plan(
    session: AsyncSession,
    admin_user_id: int,
    org_id: int,
    *,
    plan: str,
    mrr_eur: float | None = None,
    subscription_status: str | None = None,
    notes: str | None = None,
) -> Subscription | None:
    """Met à jour l'abonnement (plan/MRR/statut). Crée l'abonnement s'il manque. Audité."""
    if plan not in {p.value for p in Plan}:
        raise ValueError(f"Plan invalide : {plan}")
    with tenant_context(None):
        org = await session.get(Organization, org_id)
        if org is None:
            return None
        sub = await session.scalar(
            select(Subscription).where(Subscription.organization_id == org_id)
        )
        if sub is None:
            sub = Subscription(organization_id=org_id, started_on=date.today().isoformat())
            session.add(sub)
        sub.plan = Plan(plan)
        if mrr_eur is not None:
            sub.mrr_eur = mrr_eur
        if subscription_status and subscription_status in {s.value for s in SubscriptionStatus}:
            sub.status = SubscriptionStatus(subscription_status)
        if notes is not None:
            sub.notes = notes
        await platform_audit(
            session,
            admin_user_id,
            "set_plan",
            org_id=org_id,
            detail={"plan": plan, "mrr_eur": mrr_eur, "status": subscription_status},
        )
        await session.commit()
    return sub
