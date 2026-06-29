def test_list_invoices(client):
    resp = client.get("/api/v1/invoices")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    # L'état est partagé entre tests (sqlite mémoire) : on cherche une facture
    # validée (avec lignes), sans présumer de l'ordre de la liste.
    assert all("lines" in inv for inv in data["items"])
    assert any(len(inv["lines"]) >= 1 for inv in data["items"])
