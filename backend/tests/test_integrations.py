"""Tests ouverture : clés API (accès programmatique) + webhooks sortants signés."""

from __future__ import annotations

import asyncio

import httpx

from app.services import webhook_service
from tests.conftest import _login


# --- Clés API ----------------------------------------------------------------
def test_api_key_create_list_and_use(anon_client):
    owner = _login(anon_client, "admin@test.local")
    anon_client.headers["Authorization"] = f"Bearer {owner}"
    created = anon_client.post("/api/v1/api-keys", json={"name": "n8n prod"})
    assert created.status_code == 201, created.text
    body = created.json()
    full = body["key"]
    assert full.startswith("mh_") and body["prefix"].startswith("mh_")

    # La liste ne ré-expose jamais la clé complète.
    listed = anon_client.get("/api/v1/api-keys").json()
    assert listed["total"] >= 1
    assert all("key" not in item for item in listed["items"])

    # Utilisation par clé API (sans Bearer) : accès programmatique.
    anon_client.headers.pop("Authorization", None)
    anon_client.headers["X-API-Key"] = full
    r = anon_client.get("/api/v1/catalog/products")
    assert r.status_code == 200, r.text
    anon_client.headers.pop("X-API-Key", None)


def test_api_key_revoke_blocks_access(anon_client):
    owner = _login(anon_client, "admin@test.local")
    anon_client.headers["Authorization"] = f"Bearer {owner}"
    created = anon_client.post("/api/v1/api-keys", json={"name": "tmp"}).json()
    full, kid = created["key"], created["id"]
    anon_client.delete(f"/api/v1/api-keys/{kid}")

    anon_client.headers.pop("Authorization", None)
    anon_client.headers["X-API-Key"] = full
    r = anon_client.get("/api/v1/catalog/products")
    anon_client.headers.pop("X-API-Key", None)
    assert r.status_code == 401


def test_api_key_management_owner_only(anon_client):
    viewer = _login(anon_client, "viewer@test.local")  # read_only
    anon_client.headers["Authorization"] = f"Bearer {viewer}"
    assert anon_client.post("/api/v1/api-keys", json={"name": "x"}).status_code == 403


def test_api_key_is_tenant_scoped(anon_client):
    # Clé créée par l'org A : ne doit voir que les produits de A.
    owner = _login(anon_client, "admin@test.local")
    anon_client.headers["Authorization"] = f"Bearer {owner}"
    full = anon_client.post("/api/v1/api-keys", json={"name": "isoA"}).json()["key"]
    anon_client.headers.pop("Authorization", None)
    anon_client.headers["X-API-Key"] = full
    skus = {p["sku"] for p in anon_client.get("/api/v1/catalog/products").json()["items"]}
    anon_client.headers.pop("X-API-Key", None)
    assert "ORGB-ONLY" not in skus  # produit de l'org B invisible


# --- Webhooks ----------------------------------------------------------------
def test_webhook_crud(anon_client):
    owner = _login(anon_client, "admin@test.local")
    anon_client.headers["Authorization"] = f"Bearer {owner}"
    created = anon_client.post(
        "/api/v1/webhooks", json={"url": "https://hook.example/n8n", "events": "alert_created"}
    )
    assert created.status_code == 201, created.text
    assert created.json()["secret"]  # secret montré une fois
    wid = created.json()["id"]
    assert anon_client.get("/api/v1/webhooks").json()["total"] >= 1
    assert anon_client.delete(f"/api/v1/webhooks/{wid}").status_code == 200


def test_webhook_signature():
    sig = webhook_service.sign("s3cr3t", b'{"event":"x"}')
    assert sig == webhook_service.sign("s3cr3t", b'{"event":"x"}')  # déterministe
    assert sig != webhook_service.sign("other", b'{"event":"x"}')


def test_webhook_delivery_signed_and_tenant_scoped():
    """deliver() ne touche que les endpoints de l'org, signe, et respecte l'abonnement."""
    import app.models as m
    from app.core.tenancy import tenant_context
    from app.models.webhook import WebhookEndpoint
    from tests.conftest import TestSession

    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200)

    async def run() -> None:
        async with TestSession() as s:
            org_a = m.Organization(name="WH A", slug="wh-a")
            org_b = m.Organization(name="WH B", slug="wh-b")
            s.add_all([org_a, org_b])
            await s.flush()
            # flush DANS le tenant_context, sinon organization_id n'est pas estampillé.
            with tenant_context(org_a.id):
                s.add(
                    WebhookEndpoint(
                        url="https://a.example/hook", secret="secretA", events="alert_created"
                    )
                )
                await s.flush()
            with tenant_context(org_b.id):  # abonné à tout, mais autre org
                s.add(WebhookEndpoint(url="https://b.example/hook", secret="secretB", events="*"))
                await s.flush()

            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            try:
                n = await webhook_service.deliver(
                    s, org_a.id, "alert_created", {"id": 1}, client=client
                )
                # Event non abonné → 0 livraison.
                n2 = await webhook_service.deliver(
                    s, org_a.id, "stock_low", {"id": 2}, client=client
                )
            finally:
                await client.aclose()

        assert n == 1 and n2 == 0
        assert len(captured) == 1
        req = captured[0]
        assert "a.example" in str(req.url)  # org B jamais contactée (isolation)
        expected = "sha256=" + webhook_service.sign("secretA", req.content)
        assert req.headers["X-MyHanout-Signature"] == expected

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(run())
    finally:
        loop.close()
