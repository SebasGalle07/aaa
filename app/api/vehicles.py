from __future__ import annotations

"""Endpoints relacionados con vehiculos."""

from dataclasses import asdict
from datetime import datetime, date
from http import HTTPStatus
from typing import Iterable, Optional

from flask import g, jsonify, request

from app.api.decorators import require_auth, require_roles
from app.services import ReservationService, VehicleService

from . import api_bp

vehicle_service = VehicleService()
reservation_service = ReservationService()


def _parse_positive_int(value: str | None, default: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return max(0, parsed)


def _parse_float(value: Optional[str]) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError("Los valores de precio deben ser numericos.") from exc


def _parse_date(value: Optional[str]) -> Optional[date]:
    if value is None or value == "":
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Las fechas deben tener el formato AAAA-MM-DD.") from exc


def _obtener_payload(*claves: str, default: Optional[str] = None) -> Optional[str]:
    """Obtener un valor desde form-data o JSON usando varios alias."""
    for clave in claves:
        if clave in request.form:
            return request.form.get(clave, default)
    if request.is_json:
        cuerpo = request.get_json(silent=True) or {}
        for clave in claves:
            if clave in cuerpo:
                valor = cuerpo.get(clave)
                return None if valor is None else str(valor)
    return default


def _obtener_archivos(claves: Iterable[str]) -> list:
    archivos: list = []
    vistos: set[int] = set()
    for clave in claves:
        for archivo in request.files.getlist(clave):
            identificador = id(archivo)
            if identificador in vistos:
                continue
            vistos.add(identificador)
            archivos.append(archivo)
    if not archivos and request.files:
        for archivo in request.files.values():
            identificador = id(archivo)
            if identificador in vistos:
                continue
            vistos.add(identificador)
            archivos.append(archivo)
    return archivos


@api_bp.get("/vehicles/cities")
def list_vehicle_cities():
    """Obtener el catalogo de ciudades disponibles para filtros."""
    try:
        ciudades = vehicle_service.listar_ciudades()
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.SERVICE_UNAVAILABLE

    return jsonify({"items": ciudades})


@api_bp.get("/vehicles")
def list_vehicles():
    """Buscar vehiculos aplicando filtros opcionales."""
    limit = _parse_positive_int(request.args.get("limit"), 20)
    offset = _parse_positive_int(request.args.get("offset"), 0)
    limit = min(limit, 100)

    ciudad = request.args.get("ciudad")
    tipo = request.args.get("tipo")

    try:
        precio_min = _parse_float(request.args.get("precio_min"))
        precio_max = _parse_float(request.args.get("precio_max"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST

    if precio_min is not None and precio_max is not None and precio_min > precio_max:
        return jsonify({"error": "El precio minimo no puede ser mayor que el precio maximo."}), HTTPStatus.BAD_REQUEST

    try:
        fecha_inicio = _parse_date(request.args.get("fecha_inicio"))
        fecha_fin = _parse_date(request.args.get("fecha_fin"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST

    if (fecha_inicio and not fecha_fin) or (fecha_fin and not fecha_inicio):
        return jsonify({"error": "Debes enviar fecha_inicio y fecha_fin juntas."}), HTTPStatus.BAD_REQUEST

    if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
        return jsonify({"error": "La fecha de inicio no puede ser posterior a la fecha final."}), HTTPStatus.BAD_REQUEST

    try:
        resultado = vehicle_service.buscar_vehiculos(
            ciudad=ciudad,
            tipo=tipo,
            precio_min=precio_min,
            precio_max=precio_max,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            limit=limit,
            offset=offset,
        )
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.SERVICE_UNAVAILABLE

    respuesta = {
        "items": [asdict(vehicle) for vehicle in resultado["items"]],
        "total": resultado["total"],
        "limit": resultado["limit"],
        "offset": resultado["offset"],
    }
    return jsonify(respuesta)


@api_bp.get("/vehicles/<vehicle_id>")
def get_vehicle(vehicle_id: str):
    """Obtener el detalle de un vehiculo por identificador."""
    try:
        vehicle = vehicle_service.get_vehicle(vehicle_id)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.SERVICE_UNAVAILABLE

    if vehicle is None:
        return jsonify({"error": "Vehiculo no encontrado"}), HTTPStatus.NOT_FOUND

    return jsonify(asdict(vehicle))


@api_bp.get("/vehicles/<vehicle_id>/availability")
@require_auth
@require_roles("cliente", "anfitrion", "administrador")
def get_vehicle_availability(vehicle_id: str):
    """Obtener las reservas existentes de un vehiculo para validar disponibilidad."""
    include_past = request.args.get("include_past", "").lower() in {"1", "true", "yes"}

    try:
        reservas = reservation_service.obtener_disponibilidad_vehiculo(
            vehicle_id,
            incluir_historial=include_past,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except RuntimeError as exc:  # pragma: no cover - propagacion generica
        return jsonify({"error": str(exc)}), HTTPStatus.SERVICE_UNAVAILABLE

    return jsonify(
        {
            "vehicle_id": vehicle_id,
            "reservations": reservas,
        }
    )


@api_bp.post("/vehicles")
@require_auth
@require_roles("administrador")
def create_vehicle():
    """Registrar un vehiculo y dejarlo pendiente de validacion."""
    usuario = getattr(g, "current_user", None) or {}
    archivos = _obtener_archivos(["images", "imagenes", "photos", "imagenes[]", "images[]"])

    payload = {
        "license_plate": _obtener_payload("license_plate", "placa"),
        "make": _obtener_payload("make", "marca"),
        "model": _obtener_payload("model", "modelo"),
        "year": _obtener_payload("year", "anio"),
        "vehicle_type": _obtener_payload("vehicle_type", "category", "categoria"),
        "price_per_day": _obtener_payload("price_per_day", "precio", "precio_por_dia"),
        "location": _obtener_payload("location", "ciudad", "ubicacion"),
        "descripcion": _obtener_payload("description", "descripcion"),
        "capacity": _obtener_payload("capacity", "capacidad"),
        "owner_id": _obtener_payload("owner_id", "propietario_id"),
    }

    try:
        vehicle = vehicle_service.registrar_vehiculo(
            images=archivos,
            created_by=usuario.get("id"),
            **payload,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.SERVICE_UNAVAILABLE

    return jsonify(asdict(vehicle)), HTTPStatus.CREATED


@api_bp.get("/admin/vehicles/<vehicle_id>")
@require_auth
@require_roles("administrador")
def admin_get_vehicle(vehicle_id: str):
    """Obtener el detalle de un vehiculo (incluye inactivos) para uso administrativo."""
    try:
        vehicle = vehicle_service.get_vehicle(vehicle_id, include_inactive=True)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.SERVICE_UNAVAILABLE

    if vehicle is None:
        return jsonify({"error": "Vehiculo no encontrado"}), HTTPStatus.NOT_FOUND

    return jsonify(asdict(vehicle))


@api_bp.get("/admin/vehicles")
@require_auth
@require_roles("administrador")
def admin_list_vehicles():
    """Listar vehiculos para el panel administrativo."""
    limit = min(_parse_positive_int(request.args.get("limit"), 20), 200)
    offset = _parse_positive_int(request.args.get("offset"), 0)
    estado = request.args.get("estado") or request.args.get("status")
    ciudad = request.args.get("ciudad")

    try:
        resultado = vehicle_service.listar_admin(
            status=estado,
            ciudad=ciudad,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.SERVICE_UNAVAILABLE

    return jsonify(
        {
            "items": [asdict(vehicle) for vehicle in resultado["items"]],
            "total": resultado["total"],
            "limit": resultado["limit"],
            "offset": resultado["offset"],
        }
    )


@api_bp.patch("/vehicles/<vehicle_id>/status")
@require_auth
@require_roles("administrador")
def update_vehicle_status(vehicle_id: str):
    """Actualizar el estado de publicacion de un vehiculo."""
    nuevo_estado = _obtener_payload("status", "estado")
    if not nuevo_estado:
        return jsonify({"error": "Debes indicar el estado deseado."}), HTTPStatus.BAD_REQUEST

    usuario = getattr(g, "current_user", None) or {}

    try:
        vehicle = vehicle_service.actualizar_estado(
            vehicle_id,
            estado=nuevo_estado,
            usuario_validador=usuario.get("id"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.SERVICE_UNAVAILABLE

    return jsonify(asdict(vehicle))
