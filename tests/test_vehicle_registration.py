from __future__ import annotations

from io import BytesIO

import pytest
from flask import current_app
from werkzeug.datastructures import FileStorage

from app import create_app
from app.config import TestConfig
from app.models import Vehicle
from app.services.vehicle_service import VehicleService


@pytest.fixture
def test_app():
    app = create_app(TestConfig)
    app.json.sort_keys = False
    return app


@pytest.fixture
def app_context(test_app):
    with test_app.app_context():
        yield


@pytest.fixture
def admin_client(test_app):
    with test_app.test_client() as client:
        yield client


@pytest.fixture
def mock_admin_auth(monkeypatch):
    from app.api import decorators as decorators_module

    class RepoStub:
        def obtener_por_id(self, user_id: str):
            return {"id": user_id, "email": "admin@example.com", "rol": "administrador"}

    monkeypatch.setattr(decorators_module, "decode_token", lambda token: {"sub": "admin-1"})
    monkeypatch.setattr(decorators_module, "UserRepository", lambda: RepoStub())


def _archivo_imagen(contenido: bytes, nombre: str = "foto.jpg", mimetype: str = "image/jpeg") -> FileStorage:
    return FileStorage(stream=BytesIO(contenido), filename=nombre, content_type=mimetype)


class RepoNoOp:
    def crear_vehiculo(self, payload):
        raise AssertionError("No deberia invocarse crear_vehiculo")

    def actualizar_vehiculo(self, vehicle_id, payload):
        raise AssertionError("No deberia invocarse actualizar_vehiculo")

    def delete(self, filters):
        raise AssertionError("No deberia invocarse delete")


def test_vehicle_service_registrar_exitoso(app_context, monkeypatch):

    class RepoStub:
        def __init__(self):
            self.created = None
            self.updated = None
            self.deleted = []

        def crear_vehiculo(self, payload):
            self.created = dict(payload)
            data = dict(payload)
            data["id"] = "veh-123"
            return data

        def actualizar_vehiculo(self, vehicle_id, payload):
            self.updated = (vehicle_id, dict(payload))
            data = dict(self.created)
            data.update(payload)
            data["id"] = vehicle_id
            return data

        def delete(self, filters):
            self.deleted.append(filters)
            return None

    repo_stub = RepoStub()
    service = VehicleService(repository=repo_stub)

    monkeypatch.setattr(
        VehicleService,
        "_subir_imagenes",
        lambda self, vehicle_id, imagenes, bucket_name: [
            {"url": "https://cdn.example/veh-123/01.jpg", "path": f"vehicles/{vehicle_id}/01.jpg", "content_type": "image/jpeg"}
        ],
    )
    monkeypatch.setattr(VehicleService, "_eliminar_imagenes", lambda *args, **kwargs: None)

    imagen = _archivo_imagen(b"fake-image-data", "auto.JPG")

    vehicle = service.registrar_vehiculo(
        license_plate="abc123",
        make="Toyota",
        model="RAV4",
        year="2022",
        vehicle_type="SUV",
        price_per_day="120.50",
        location="Bogota",
        descripcion="SUV urbana",
        capacity="5",
        owner_id="owner-1",
        created_by="admin-1",
        images=[imagen],
    )

    assert vehicle.id == "veh-123"
    assert vehicle.status == VehicleService.STATUS_INACTIVE
    assert vehicle.images and vehicle.images[0]["url"].startswith("https://cdn.example/")
    assert repo_stub.created["license_plate"] == "ABC123"
    assert repo_stub.updated[0] == "veh-123"


def test_vehicle_service_respeta_anio_minimo(app_context):
    current_app.config["VEHICLE_MIN_YEAR"] = 2020
    service = VehicleService(repository=RepoNoOp())

    imagen = _archivo_imagen(b"fake-image-data")

    with pytest.raises(ValueError) as excinfo:
        service.registrar_vehiculo(
            license_plate="abc123",
            make="Toyota",
            model="Corolla",
            year="2015",
            vehicle_type="Sedan",
            price_per_day="90",
            location="Bogota",
            images=[imagen],
        )

    assert "2020" in str(excinfo.value)


def test_vehicle_service_valida_tamano_imagen(app_context):
    current_app.config["VEHICLE_IMAGE_MAX_MB"] = 0.001  # ~1KB
    service = VehicleService(repository=RepoNoOp())
    contenido = b"x" * 2048  # 2KB
    imagen = _archivo_imagen(contenido)

    with pytest.raises(ValueError) as excinfo:
        service.registrar_vehiculo(
            license_plate="abc123",
            make="Toyota",
            model="RAV4",
            year="2022",
            vehicle_type="SUV",
            price_per_day="120",
            location="Bogota",
            images=[imagen],
        )

    assert "maximo" in str(excinfo.value).lower()


def test_admin_create_vehicle_endpoint(monkeypatch, admin_client, mock_admin_auth):
    from app.api import vehicles as vehicles_module

    class ServiceStub:
        def __init__(self):
            self.payload = None

        def registrar_vehiculo(self, **kwargs):
            self.payload = kwargs
            return Vehicle(
                id="veh-1",
                license_plate="ABC123",
                status="inactivo",
                make="Toyota",
                model="RAV4",
                year=2022,
                vehicle_type="suv",
                price_per_day=120.0,
                currency="USD",
                location="Bogota",
                images=[{"url": "https://cdn.example/veh-1/01.jpg", "path": "vehicles/veh-1/01.jpg", "content_type": "image/jpeg"}],
            )

    service_stub = ServiceStub()
    monkeypatch.setattr(vehicles_module, "vehicle_service", service_stub)

    response = admin_client.post(
        "/api/vehicles",
        headers={"Authorization": "Bearer token"},
        data={
            "placa": "abc123",
            "marca": "Toyota",
            "modelo": "RAV4",
            "anio": "2022",
            "categoria": "suv",
            "precio": "120",
            "ciudad": "Bogota",
            "descripcion": "SUV amplia",
            "images": (BytesIO(b"fake"), "foto.jpg"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    assert service_stub.payload is not None
    assert service_stub.payload["created_by"] == "admin-1"
    assert len(service_stub.payload["images"]) == 1
    data = response.get_json()
    assert data["status"] == "inactivo"


def test_admin_create_vehicle_error(monkeypatch, admin_client, mock_admin_auth):
    from app.api import vehicles as vehicles_module

    class ServiceStub:
        def registrar_vehiculo(self, **kwargs):
            raise ValueError("Formato invalido")

    monkeypatch.setattr(vehicles_module, "vehicle_service", ServiceStub())

    response = admin_client.post(
        "/api/vehicles",
        headers={"Authorization": "Bearer token"},
        data={
            "placa": "abc123",
            "marca": "Toyota",
            "modelo": "RAV4",
            "anio": "2022",
            "categoria": "suv",
            "precio": "120",
            "ciudad": "Bogota",
            "images": (BytesIO(b"fake"), "foto.jpg"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "invalido" in response.get_json()["error"].lower()


def test_admin_update_vehicle_status(monkeypatch, admin_client, mock_admin_auth):
    from app.api import vehicles as vehicles_module

    class ServiceStub:
        def __init__(self):
            self.calls = []

        def actualizar_estado(self, vehicle_id: str, *, estado: str, usuario_validador: str | None = None):
            self.calls.append((vehicle_id, estado, usuario_validador))
            return Vehicle(
                id=vehicle_id,
                license_plate="XYZ987",
                status=estado,
                make="Ford",
                model="Ranger",
                year=2023,
                vehicle_type="pickup",
                price_per_day=150.0,
                currency="USD",
            )

    service_stub = ServiceStub()
    monkeypatch.setattr(vehicles_module, "vehicle_service", service_stub)

    response = admin_client.patch(
        "/api/vehicles/veh-9/status",
        headers={"Authorization": "Bearer token"},
        json={"status": "activo"},
    )

    assert response.status_code == 200
    assert service_stub.calls == [("veh-9", "activo", "admin-1")]
    assert response.get_json()["status"] == "activo"


def test_admin_list_vehicles(monkeypatch, admin_client, mock_admin_auth):
    from app.api import vehicles as vehicles_module

    class ServiceStub:
        def listar_admin(self, **kwargs):
            return {
                "items": [
                    Vehicle(
                        id="veh-1",
                        license_plate="ABC123",
                        status="inactivo",
                        make="Toyota",
                        model="RAV4",
                        year=2022,
                        vehicle_type="suv",
                        price_per_day=120.0,
                        currency="USD",
                    )
                ],
                "total": 1,
                "limit": kwargs["limit"],
                "offset": kwargs["offset"],
            }

    monkeypatch.setattr(vehicles_module, "vehicle_service", ServiceStub())

    response = admin_client.get(
        "/api/admin/vehicles?estado=inactivo",
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] == 1
    assert data["items"][0]["license_plate"] == "ABC123"


def test_admin_get_vehicle(monkeypatch, admin_client, mock_admin_auth):
    from app.api import vehicles as vehicles_module

    class ServiceStub:
        def __init__(self):
            self.called = False

        def get_vehicle(self, vehicle_id: str, *, include_inactive: bool = False):
            assert include_inactive is True
            self.called = True
            return Vehicle(
                id=vehicle_id,
                license_plate="ABC123",
                status="inactivo",
                make="Toyota",
                model="RAV4",
                year=2022,
                vehicle_type="suv",
                price_per_day=120.0,
                currency="USD",
            )

    service_stub = ServiceStub()
    monkeypatch.setattr(vehicles_module, "vehicle_service", service_stub)

    response = admin_client.get(
        "/api/admin/vehicles/veh-1",
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 200
    assert service_stub.called is True
    data = response.get_json()
    assert data["license_plate"] == "ABC123"
