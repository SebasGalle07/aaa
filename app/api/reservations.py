from __future__ import annotations

"""Endpoints relacionados con las reservas de los usuarios."""

from dataclasses import asdict
from http import HTTPStatus

from flask import jsonify, g, request

from app.api.decorators import require_auth, require_roles
from app.services import ReservationService

from . import api_bp

reservation_service = ReservationService()


@api_bp.get("/reservations")
@require_auth
@require_roles("cliente", "anfitrion", "administrador")
def listar_reservas():
    """Listar paginado de reservas del usuario autenticado."""
    usuario = g.current_user
    limit = min(max(int(request.args.get("limit", 20)), 1), 100)
    offset = max(int(request.args.get("offset", 0)), 0)

    try:
        resultado = reservation_service.listar_reservas(usuario["id"], limit=limit, offset=offset)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.SERVICE_UNAVAILABLE

    respuesta = {
        "items": [asdict(reserva) for reserva in resultado["items"]],
        "total": resultado["total"],
        "limit": limit,
        "offset": offset,
    }
    return jsonify(respuesta)


@api_bp.post("/reservations")
@require_auth
@require_roles("cliente", "administrador")
def crear_reserva():
    """Crear una reserva para el usuario autenticado."""
    usuario = g.current_user
    payload = request.get_json(silent=True) or {}

    try:
        resultado = reservation_service.crear_reserva(
            usuario_id=usuario["id"],
            vehicle_id=payload.get("vehicle_id"),
            start_date=payload.get("start_date"),
            end_date=payload.get("end_date"),
            comentarios=payload.get("comentarios"),
            metodo_pago=payload.get("metodo_pago", "tarjeta"),
            card_last4=payload.get("card_last4"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.SERVICE_UNAVAILABLE

    respuesta = {
        "reserva": asdict(resultado["reserva"]),
        "pago": asdict(resultado["pago"]),
    }
    monto = respuesta["pago"].get("amount")
    if monto is not None:
        respuesta["pago"]["amount"] = str(monto)

    return jsonify(respuesta), HTTPStatus.CREATED


@api_bp.post("/reservations/<reserva_id>/cancel")
@require_auth
@require_roles("cliente", "administrador")
def cancelar_reserva(reserva_id: str):
    """Cancelar una reserva si pertenece al usuario y esta confirmada."""
    usuario = g.current_user

    try:
        reserva = reservation_service.cancelar_reserva(
            reserva_id,
            usuario["id"],
            is_admin=usuario["rol"].lower() == "administrador",
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.SERVICE_UNAVAILABLE

    return jsonify(asdict(reserva))
