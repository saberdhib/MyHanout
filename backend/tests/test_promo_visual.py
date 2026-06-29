"""Génération d'affiche promo (provider image mock, keyless)."""

import asyncio

from app.intelligence.imaging import get_image_provider


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_mock_image_provider_returns_data_url():
    provider = get_image_provider()
    image = _run(provider.generate("Promo -30% sur boeuf haché"))
    assert image.provider == "mock"
    assert image.data_url.startswith("data:image/svg+xml;base64,")
    assert image.prompt


def _make_campaign(org_id: int) -> int:
    """Crée une campagne promo brouillon dans l'org A (tenant-scopé)."""
    from app.core.tenancy import tenant_context
    from app.models.promo import PromoCampaign

    from .conftest import TestSession

    async def _create() -> int:
        async with TestSession() as s:
            with tenant_context(org_id):
                c = PromoCampaign(title="Promo test", message="−30% boeuf", discount_pct=30)
                s.add(c)
                await s.flush()
                cid = c.id
                await s.commit()
            return cid

    return _run(_create())


def test_generate_visual_endpoint(client):
    promo_id = _make_campaign(1)  # org A
    resp = client.post(f"/api/v1/promos/{promo_id}/visual")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["visual_url"].startswith("data:image/")
    assert data["visual_prompt"]
