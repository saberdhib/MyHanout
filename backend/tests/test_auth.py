"""Tests d'authentification JWT + RBAC."""


def test_login_ok(anon_client):
    resp = anon_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.local", "password": "secret"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["refresh_token"]


def test_login_bad_password(anon_client):
    resp = anon_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.local", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_protected_route_requires_token(anon_client):
    assert anon_client.get("/api/v1/stocks").status_code == 401


def test_protected_route_with_token(client):
    assert client.get("/api/v1/stocks").status_code == 200


def test_me_returns_role(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["role"] == "owner"


def test_rbac_read_only_can_view_but_not_order(viewer_client):
    # read_only consulte les factures...
    assert viewer_client.get("/api/v1/invoices").status_code == 200
    # ...mais n'a pas le scope "orders" -> 403 sur une action commande.
    assert viewer_client.post("/api/v1/orders/1/approve").status_code == 403


def test_refresh_issues_new_access_token(anon_client):
    login = anon_client.post(
        "/api/v1/auth/login",
        json={"email": "accountant@test.local", "password": "secret"},
    ).json()
    resp = anon_client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_refresh_rejects_access_token(anon_client):
    login = anon_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.local", "password": "secret"},
    ).json()
    # Un access token ne doit pas être accepté comme refresh.
    resp = anon_client.post("/api/v1/auth/refresh", json={"refresh_token": login["access_token"]})
    assert resp.status_code == 401
