import pytest

from app import create_app
from app.config import TestConfig
from app.services import CredencialesInvalidasError


@pytest.fixture
def test_client(monkeypatch):
    app = create_app(TestConfig)
    with app.test_client() as client:
        yield client


def test_login_exitoso(monkeypatch, test_client):
    from app.api import auth as auth_module

    class AuthServiceStub:
        def autenticar(self, email: str, password: str):
            assert email == "juan@example.com"
            assert password == "ContrasenaSegura"
            return {
                "id": "123",
                "email": email,
                "nombre": "Juan Perez",
                "rol": "cliente",
                "created_at": "2025-01-01T00:00:00Z",
                "access_token": "token-de-prueba",
            }

    monkeypatch.setattr(auth_module, "auth_service", AuthServiceStub())

    response = test_client.post(
        "/api/auth/login",
        json={"email": "juan@example.com", "password": "ContrasenaSegura"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["access_token"] == "token-de-prueba"


def test_login_credenciales_invalidas(monkeypatch, test_client):
    from app.api import auth as auth_module

    class AuthServiceStub:
        def autenticar(self, email: str, password: str):
            raise CredencialesInvalidasError("Credenciales invalidas.")

    monkeypatch.setattr(auth_module, "auth_service", AuthServiceStub())

    response = test_client.post(
        "/api/auth/login",
        json={"email": "juan@example.com", "password": "incorrecta"},
    )

    assert response.status_code == 401
    assert "credenciales" in response.get_json()["error"].lower()
