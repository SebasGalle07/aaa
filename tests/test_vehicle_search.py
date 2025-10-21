from datetime import date

import pytest

from app import create_app
from app.config import TestConfig
from app.models import Vehicle


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


def test_list_vehicles_con_filtros(monkeypatch, test_client):
    from app.api import vehicles as vehicles_module

    class ServicioStub:
        def buscar_vehiculos(self, **kwargs):
            assert kwargs["ciudad"] == "Bogota"
            assert kwargs["tipo"] == "suv"
            assert kwargs["precio_min"] == 50
            assert kwargs["precio_max"] == 150
            assert kwargs["fecha_inicio"] == date(2025, 10, 10)
            assert kwargs["fecha_fin"] == date(2025, 10, 15)
            return {
                "items": [
                    Vehicle(
                        id="vehiculo-1",
                        owner_id="owner-1",
                        make="Toyota",
                        model="RAV4",
                        year=2022,
                        vehicle_type="suv",
                        price_per_day=120.0,
                        currency="USD",
                        description="SUV amplia",
                        location="Bogota",
                        capacity=5,
                        created_at="2025-01-01T00:00:00Z",
                        updated_at="2025-01-02T00:00:00Z",
                    )
                ],
                "total": 1,
                "limit": kwargs["limit"],
                "offset": kwargs["offset"],
            }

    monkeypatch.setattr(vehicles_module, "vehicle_service", ServicioStub())

    response = test_client.get(
        "/api/vehicles?ciudad=Bogota&tipo=suv&precio_min=50&precio_max=150&fecha_inicio=2025-10-10&fecha_fin=2025-10-15"
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["vehicle_type"] == "suv"


def test_list_vehicles_precios_invalidos(monkeypatch, test_client):
    response = test_client.get("/api/vehicles?precio_min=abc")
    assert response.status_code == 400
    assert "precio" in response.get_json()["error"].lower()


def test_list_vehicles_fechas_invalidas(monkeypatch, test_client):
    response = test_client.get("/api/vehicles?fecha_inicio=2025-13-01&fecha_fin=2025-14-01")
    assert response.status_code == 400
    assert "formato" in response.get_json()["error"].lower()


def test_list_vehicles_sin_fecha_fin(monkeypatch, test_client):
    response = test_client.get("/api/vehicles?fecha_inicio=2025-10-01")
    assert response.status_code == 400
    assert "fecha_fin" in response.get_json()["error"].lower()


def test_vehicle_service_filtra_disponibilidad_con_paginacion():
    from app.services.vehicle_service import VehicleService

    class VehicleRepoStub:
        def __init__(self):
            self.last_call = {}

        def search(self, **kwargs):
            self.last_call = kwargs
            data = [
                {
                    "id": "vehiculo-libre",
                    "owner_id": "owner-1",
                    "make": "Toyota",
                    "model": "RAV4",
                    "year": 2022,
                    "vehicle_type": "suv",
                    "price_per_day": 120.0,
                    "currency": "USD",
                    "description": "SUV amplia",
                    "location": "Bogota",
                    "capacity": 5,
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                {
                    "id": "vehiculo-ocupado",
                    "owner_id": "owner-2",
                    "make": "Ford",
                    "model": "Ranger",
                    "year": 2023,
                    "vehicle_type": "pickup",
                    "price_per_day": 150.0,
                    "currency": "USD",
                    "description": "Pickup 4x4",
                    "location": "Bogota",
                    "capacity": 5,
                    "created_at": "2025-01-01T00:00:00Z",
                    "updated_at": "2025-01-01T00:00:00Z",
                },
            ]
            return type("Resp", (), {"data": data})()

    class ReservationRepoStub:
        def obtener_reservas_en_rango(self, vehicle_ids, fecha_inicio, fecha_fin):
            data = [{"vehicle_id": "vehiculo-ocupado"}]
            return type("Resp", (), {"data": data})()

    repo_stub = VehicleRepoStub()
    reservation_stub = ReservationRepoStub()
    service = VehicleService(repository=repo_stub, reservation_repository=reservation_stub)

    resultado = service.buscar_vehiculos(
        fecha_inicio=date(2025, 10, 10),
        fecha_fin=date(2025, 10, 12),
        limit=1,
        offset=0,
    )

    assert repo_stub.last_call["limit"] is None
    assert resultado["total"] == 1
    assert len(resultado["items"]) == 1
    assert resultado["items"][0].id == "vehiculo-libre"
