from __future__ import annotations

"""Endpoints relacionados con vehiculos."""

from dataclasses import asdict
from datetime import datetime, date
from typing import Optional

from flask import jsonify, request

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
    except ValueError:
        raise ValueError("Los valores de precio deben ser numericos.")


def _parse_date(value: Optional[str]) -> Optional[date]:
    if value is None or value == "":
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Las fechas deben tener el formato AAAA-MM-DD.") from exc


@api_bp.get("/vehicles/cities")
def list_vehicle_cities():
    """Obtener el catalogo de ciudades disponibles para filtros."""
    try:
        ciudades = vehicle_service.listar_ciudades()
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503

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
        return jsonify({"error": str(exc)}), 400

    if precio_min is not None and precio_max is not None and precio_min > precio_max:
        return jsonify({"error": "El precio minimo no puede ser mayor que el precio maximo."}), 400

    try:
        fecha_inicio = _parse_date(request.args.get("fecha_inicio"))
        fecha_fin = _parse_date(request.args.get("fecha_fin"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if (fecha_inicio and not fecha_fin) or (fecha_fin and not fecha_inicio):
        return jsonify({"error": "Debes enviar fecha_inicio y fecha_fin juntas."}), 400

    if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
        return jsonify({"error": "La fecha de inicio no puede ser posterior a la fecha final."}), 400

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
        return jsonify({"error": str(exc)}), 503

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
        return jsonify({"error": str(exc)}), 503

    if vehicle is None:
        return jsonify({"error": "Vehiculo no encontrado"}), 404

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
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:  # pragma: no cover - propagacion generica
        return jsonify({"error": str(exc)}), 503

    return jsonify(
        {
            "vehicle_id": vehicle_id,
            "reservations": reservas,
        }
    )
