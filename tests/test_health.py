from app import create_app
from app.config import TestConfig


def test_health_endpoint():
    app = create_app(TestConfig)
    client = app.test_client()

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["estado"] == "operativo"
    assert "supabase" in payload
    assert "marca_de_tiempo" in payload
