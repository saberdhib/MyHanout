def test_list_invoices(client):
    resp = client.get("/api/v1/invoices")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    inv = data["items"][0]
    assert "lines" in inv
    assert len(inv["lines"]) >= 1
