def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_metrics(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "myhanout_requests_total" in resp.text
