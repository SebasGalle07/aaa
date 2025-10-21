from datetime import date
from decimal import Decimal
import pytest

from app import create_app
from app.config import TestConfig
from app.models import Payment, Reservation


@pytest.fixture
def test_client():
    app = create_app(TestConfig)
    app.json.sort_keys = False
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_auth(monkeypatch):
    from app.api import decorators as decorators_module

    class RepoStub:
        def obtener_por_id(self, user_id: str):
            return {"id": user_id, "email": "usuario@example.com", "rol": "cliente"}

    monkeypatch.setattr(decorators_module, "decode_token", lambda token: {"sub": "usuario-1"})
    monkeypatch.setattr(decorators_module, "UserRepository", lambda: RepoStub())


def test_listar_reservas_exitoso(monkeypatch, test_client, mock_auth):
    from app.api import reservations as reservations_module

    class ServicioStub:
        def listar_reservas(self, user_id: str, limit: int, offset: int, **kwargs):
            assert user_id == "usuario-1"
            assert limit == 20
            assert offset == 0
            return {
                "items": [
                    Reservation(
                        id="res-1",
                        vehicle_id="vehiculo-1",
                        user_id="usuario-1",
                        start_date=date(2025, 10, 10),
                        end_date=date(2025, 10, 12),
                        status="confirmada",
                        created_at="2025-01-01T00:00:00Z",
                    )
                ],
                "total": 1,
            }

    monkeypatch.setattr(reservations_module, "reservation_service", ServicioStub())

    response = test_client.get(
        "/api/reservations",
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == "confirmada"


def test_listar_reservas_sin_token(test_client):
    response = test_client.get("/api/reservations")
    assert response.status_code == 401


def test_crear_reserva_exitoso(monkeypatch, test_client, mock_auth):
    from app.api import reservations as reservations_module

    class ServicioStub:
        def crear_reserva(self, **kwargs):
            assert kwargs["usuario_id"] == "usuario-1"
            assert kwargs["vehicle_id"] == "vehiculo-1"
            assert kwargs["start_date"] == "2025-12-01"
            assert kwargs["end_date"] == "2025-12-05"
            assert kwargs["metodo_pago"] == "tarjeta"
            return {
                "reserva": Reservation(
                    id="res-1",
                    vehicle_id="vehiculo-1",
                    user_id="usuario-1",
                    start_date=date(2025, 12, 1),
                    end_date=date(2025, 12, 5),
                    status="confirmada",
                    created_at="2025-01-01T00:00:00Z",
                ),
                "pago": Payment(
                    id="pay-1",
                    reservation_id="res-1",
                    user_id="usuario-1",
                    amount=Decimal("480.00"),
                    currency="USD",
                    status="pagado",
                    provider="tarjeta",
                    reference="PAY-1234567890",
                    card_last4="4242",
                    created_at="2025-01-01T00:00:00Z",
                ),
            }

    from decimal import Decimal

    monkeypatch.setattr(reservations_module, "reservation_service", ServicioStub())

    response = test_client.post(
        "/api/reservations",
        headers={"Authorization": "Bearer token"},
        json={
            "vehicle_id": "vehiculo-1",
            "start_date": "2025-12-01",
            "end_date": "2025-12-05",
            "comentarios": "Viaje de trabajo",
            "metodo_pago": None,
            "card_last4": "4242",
        },
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["reserva"]["status"] == "confirmada"
    assert data["pago"]["status"] == "pagado"
    assert data["pago"]["card_last4"] == "4242"


def test_crear_reserva_conflicto(monkeypatch, test_client, mock_auth):
    from app.api import reservations as reservations_module

    class ServicioStub:
        def crear_reserva(self, **kwargs):
            raise ValueError("El vehiculo ya esta reservado en ese rango de fechas.")

    monkeypatch.setattr(reservations_module, "reservation_service", ServicioStub())

    response = test_client.post(
        "/api/reservations",
        headers={"Authorization": "Bearer token"},
        json={
            "vehicle_id": "vehiculo-1",
            "start_date": "2025-12-01",
            "end_date": "2025-12-05",
        },
    )

    assert response.status_code == 400
    assert "reservado" in response.get_json()["error"].lower()


def test_cancelar_reserva_exitoso(monkeypatch, test_client, mock_auth):
    from app.api import reservations as reservations_module

    class ServicioStub:
        def cancelar_reserva(self, reserva_id: str, user_id: str, is_admin: bool = False):
            assert reserva_id == "res-1"
            assert user_id == "usuario-1"
            assert is_admin is False
            return Reservation(
                id=reserva_id,
                vehicle_id="vehiculo-1",
                user_id=user_id,
                start_date=date(2025, 10, 10),
                end_date=date(2025, 10, 12),
                status="cancelada",
                created_at="2025-01-01T00:00:00Z",
            )

    monkeypatch.setattr(reservations_module, "reservation_service", ServicioStub())

    response = test_client.post(
        "/api/reservations/res-1/cancel",
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "cancelada"


def test_cancelar_reserva_error(monkeypatch, test_client, mock_auth):
    from app.api import reservations as reservations_module

    class ServicioStub:
        def cancelar_reserva(self, reserva_id: str, user_id: str, is_admin: bool = False):
            raise ValueError("Solo es posible cancelar reservas en estado confirmada.")

    monkeypatch.setattr(reservations_module, "reservation_service", ServicioStub())

    response = test_client.post(
        "/api/reservations/res-1/cancel",
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 400
    assert "cancelar" in response.get_json()["error"].lower()


def test_reservations_supabase_no_configurada(monkeypatch, test_client):
    from app.api import decorators as decorators_module

    class RepoStub:
        def obtener_por_id(self, user_id: str):
            raise RuntimeError("Cliente de Supabase no inicializado. Verifica los valores de configuracion de Supabase.")

    monkeypatch.setattr(decorators_module, "decode_token", lambda token: {"sub": "usuario-1"})
    monkeypatch.setattr(decorators_module, "UserRepository", lambda: RepoStub())

    response = test_client.get(
        "/api/reservations",
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 503
    assert "supabase" in response.get_json()["error"].lower()




