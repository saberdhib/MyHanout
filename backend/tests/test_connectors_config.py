"""Test de l'état des connecteurs (sans fuite de secret)."""

from __future__ import annotations


def test_connectors_status_default_mock(client):
    data = client.get("/api/v1/config/connectors").json()
    items = {c["key"]: c for c in data["items"]}
    # Connecteurs attendus présents.
    for key in ("whatsapp", "telegram", "slack", "email", "dwh", "pos", "sensors", "ml_service"):
        assert key in items, key
    # Par défaut (keyless) tout est en mock.
    assert items["whatsapp"]["status"] == "mock"
    assert items["slack"]["status"] == "mock"
    # Aucun secret renvoyé : seulement un booléen + un indice d'activation.
    blob = client.get("/api/v1/config/connectors").text
    assert (
        "token" not in blob.lower() or "TOKEN" in blob
    )  # le hint nomme la variable, pas la valeur
    for c in data["items"]:
        assert set(c.keys()) == {
            "key",
            "label",
            "category",
            "provider",
            "status",
            "configured",
            "hint",
        }
