def test_list_stocks(client):
    resp = client.get("/api/v1/stocks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert "product_name" in data["items"][0]


def test_stock_alerts(client):
    resp = client.get("/api/v1/stocks/alerts")
    assert resp.status_code == 200
    # Le stock seedé (5) est sous le seuil (10) -> au moins une alerte.
    assert resp.json()["total"] >= 1
