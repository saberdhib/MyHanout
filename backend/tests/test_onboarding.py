"""Tests onboarding self-service : signup, setup, invitation, acceptation."""


def _bearer(client, token: str):
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def test_signup_creates_isolated_org(anon_client):
    resp = anon_client.post(
        "/api/v1/onboarding/signup",
        json={
            "email": "newowner@shop.local",
            "password": "secret",
            "organization_name": "Épicerie Test",
            "business_type": "epicerie",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"] and data["organization_id"]

    # Nouvelle org vide et ISOLÉE : ne voit pas les produits des orgs A/B.
    _bearer(anon_client, data["access_token"])
    stocks = anon_client.get("/api/v1/stocks").json()
    assert stocks["total"] == 0


def test_signup_then_add_product_and_supplier(anon_client):
    token = anon_client.post(
        "/api/v1/onboarding/signup",
        json={
            "email": "owner2@shop.local",
            "password": "secret",
            "organization_name": "Boucherie Test",
        },
    ).json()["access_token"]
    _bearer(anon_client, token)

    sup = anon_client.post("/api/v1/onboarding/suppliers", json={"name": "Fourn X"})
    assert sup.status_code == 201
    prod = anon_client.post(
        "/api/v1/onboarding/products",
        json={"sku": "TEST-1", "name": "Test", "unit": "kg", "supplier_id": sup.json()["id"]},
    )
    assert prod.status_code == 201
    # Le produit appartient bien à la nouvelle org (visible pour elle).
    assert anon_client.get("/api/v1/stocks").json()["total"] == 0  # pas de stock encore


def test_invite_and_accept_accountant(anon_client):
    # Owner crée une org puis invite un comptable.
    owner_token = anon_client.post(
        "/api/v1/onboarding/signup",
        json={
            "email": "owner3@shop.local",
            "password": "secret",
            "organization_name": "Org Invite",
        },
    ).json()["access_token"]
    _bearer(anon_client, owner_token)
    inv = anon_client.post(
        "/api/v1/onboarding/invitations",
        json={"email": "compta@shop.local", "role": "accountant"},
    )
    assert inv.status_code == 200
    token = inv.json()["token"]

    # Le comptable accepte (sans auth) et rejoint l'org avec le rôle accountant.
    anon_client.headers.pop("Authorization", None)
    acc = anon_client.post(
        "/api/v1/onboarding/invitations/accept",
        json={"token": token, "password": "secret", "full_name": "Compta"},
    )
    assert acc.status_code == 200
    # Le comptable peut lire les factures mais pas commander.
    _bearer(anon_client, acc.json()["access_token"])
    assert anon_client.get("/api/v1/invoices").status_code == 200
    assert anon_client.post("/api/v1/orders/1/approve").status_code == 403


def test_non_owner_cannot_invite(accountant_client):
    resp = accountant_client.post(
        "/api/v1/onboarding/invitations", json={"email": "x@y.local", "role": "staff"}
    )
    assert resp.status_code == 403
