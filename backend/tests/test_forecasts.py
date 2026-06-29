def test_forecast_endpoint(client):
    resp = client.get("/api/v1/forecasts/1", params={"horizon_days": 7})
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "naive"
    assert len(data["points"]) == 7
    assert data["points"][0]["yhat"] >= 0
    assert data["explanation"]
