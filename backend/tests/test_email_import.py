"""Import de factures depuis la boîte mail (provider mock, keyless)."""


def test_import_email_creates_pending_invoices(client):
    resp = client.post("/api/v1/invoices/import/email")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["provider"] == "mock"
    assert data["imported"] >= 1
    assert data["items"][0]["invoice_id"] > 0
    assert data["items"][0]["filename"].endswith(".pdf")

    # Idempotence : ré-importer les mêmes pièces ne crée pas de nouvelle facture.
    before = client.get("/api/v1/invoices").json()["total"]
    client.post("/api/v1/invoices/import/email")
    after = client.get("/api/v1/invoices").json()["total"]
    assert after == before


def test_import_email_requires_auth(anon_client):
    resp = anon_client.post("/api/v1/invoices/import/email")
    assert resp.status_code in (401, 403)
