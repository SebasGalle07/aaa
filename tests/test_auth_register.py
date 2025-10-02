import pytest

from app import create_app
from app.config import TestConfig
from app.models import User
from app.services import DatosInvalidosError, UsuarioExistenteError


@pytest.fixture
def test_client(monkeypatch):
    app = create_app(TestConfig)
    with app.test_client() as client:
        yield client


def test_registro_usuario_exitoso(monkeypatch, test_client):
    from app.api import auth as auth_module

    class UserServiceStub:
        def registrar_usuario(self, nombre, email, password, rol=None):
            assert nombre == "Juan Perez"
            assert email == "juan@example.com"
            assert password == "ContrasenaSegura"
            assert rol is None
            return User(
                id="123",
                email=email,
                rol="cliente",
                nombre=nombre,
                created_at="2025-01-01T00:00:00Z",
            )

    class AuthServiceStub:
        def generar_token_para_usuario(self, usuario):
            return "token-de-prueba"

    monkeypatch.setattr(auth_module, "user_service", UserServiceStub())
    monkeypatch.setattr(auth_module, "auth_service", AuthServiceStub())

    respuesta = test_client.post(
        "/api/auth/register",
        json={"nombre": "Juan Perez", "email": "juan@example.com", "password": "ContrasenaSegura"},
    )

    assert respuesta.status_code == 201
    data = respuesta.get_json()
    assert data == {
        "id": "123",
        "email": "juan@example.com",
        "nombre": "Juan Perez",
        "rol": "cliente",
        "creado_en": "2025-01-01T00:00:00Z",
        "access_token": "token-de-prueba",
    }


def test_registro_usuario_correo_duplicado(monkeypatch, test_client):
    from app.api import auth as auth_module

    class UserServiceStub:
        def registrar_usuario(self, nombre, email, password, rol=None):
            raise UsuarioExistenteError("Ya existe un usuario con este correo electronico.")

    monkeypatch.setattr(auth_module, "user_service", UserServiceStub())

    respuesta = test_client.post(
        "/api/auth/register",
        json={"nombre": "Ana", "email": "ana@example.com", "password": "ContrasenaSegura"},
    )

    assert respuesta.status_code == 409
    data = respuesta.get_json()
    assert data["error"] == "Ya existe un usuario con este correo electronico."


def test_registro_usuario_datos_invalidos(monkeypatch, test_client):
    from app.api import auth as auth_module

    class UserServiceStub:
        def registrar_usuario(self, nombre, email, password, rol=None):
            raise DatosInvalidosError("El nombre es obligatorio.")

    monkeypatch.setattr(auth_module, "user_service", UserServiceStub())

    respuesta = test_client.post(
        "/api/auth/register",
        json={"nombre": "", "email": "correo", "password": "123"},
    )

    assert respuesta.status_code == 400
    data = respuesta.get_json()
    assert data["error"] == "El nombre es obligatorio."


def test_registro_usuario_rol_invalido(monkeypatch, test_client):
    from app.api import auth as auth_module

    class UserServiceStub:
        def registrar_usuario(self, nombre, email, password, rol=None):
            raise DatosInvalidosError(
                "El rol seleccionado no es valido. Roles permitidos: cliente, anfitrion, administrador."
            )

    monkeypatch.setattr(auth_module, "user_service", UserServiceStub())

    respuesta = test_client.post(
        "/api/auth/register",
        json={
            "nombre": "Luis",
            "email": "luis@example.com",
            "password": "ContrasenaSegura",
            "rol": "superadmin",
        },
    )

    assert respuesta.status_code == 400
    data = respuesta.get_json()
    assert (
        data["error"]
        == "El rol seleccionado no es valido. Roles permitidos: cliente, anfitrion, administrador."
    )
