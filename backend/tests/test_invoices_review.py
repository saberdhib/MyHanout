"""Tests du parcours facture : upload -> review -> approve/reject (mock OCR)."""


def _upload(client, content: bytes):
    return client.post(
        "/api/v1/invoices/upload",
        files={"file": ("facture.pdf", content, "application/pdf")},
    )


def test_upload_creates_pending_review_no_lines(client):
    resp = _upload(client, b"contenu-unique-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending_review"
    # Aucune ligne écrite avant validation humaine.
    assert data["lines"] == []
    assert data["reasons"]  # explicabilité présente


def test_upload_is_idempotent(client):
    r1 = _upload(client, b"contenu-idempotent")
    r2 = _upload(client, b"contenu-idempotent")
    assert r1.json()["id"] == r2.json()["id"]


def test_approve_writes_lines(client):
    up = _upload(client, b"contenu-unique-approve").json()
    assert up["status"] == "pending_review"
    resp = client.post(f"/api/v1/invoices/{up['id']}/approve")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    # Le mock OCR produit 2 lignes -> écrites à l'approbation.
    assert len(data["lines"]) == 2


def test_reject_records_reason(client):
    up = _upload(client, b"contenu-unique-reject").json()
    resp = client.post(
        f"/api/v1/invoices/{up['id']}/reject",
        json={"reason": "Montant erroné"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["review_reason"] == "Montant erroné"
    assert data["lines"] == []


def test_approve_twice_fails(client):
    up = _upload(client, b"contenu-unique-double").json()
    client.post(f"/api/v1/invoices/{up['id']}/approve")
    resp = client.post(f"/api/v1/invoices/{up['id']}/approve")
    assert resp.status_code == 400
