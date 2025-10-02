from __future__ import annotations

"""Utilidades para manejo consistente de errores en la API."""

from typing import Any, Dict, Tuple

from flask import Flask, jsonify


def register_error_handlers(app: Flask) -> None:
    """Configura manejadores globales de errores para respuestas JSON limpias."""

    @app.errorhandler(400)
    def handle_bad_request(exc):  # type: ignore[override]
        payload = _build_payload("Solicitud invalida", exc)
        return jsonify(payload), 400

    @app.errorhandler(401)
    def handle_unauthorized(exc):  # type: ignore[override]
        payload = _build_payload("Autenticacion requerida", exc)
        return jsonify(payload), 401

    @app.errorhandler(403)
    def handle_forbidden(exc):  # type: ignore[override]
        payload = _build_payload("Acceso denegado", exc)
        return jsonify(payload), 403

    @app.errorhandler(404)
    def handle_not_found(exc):  # type: ignore[override]
        payload = _build_payload("Recurso no encontrado", exc)
        return jsonify(payload), 404

    @app.errorhandler(500)
    def handle_internal_error(exc):  # type: ignore[override]
        app.logger.exception("Error inesperado", exc_info=exc)
        payload = {"error": "Ha ocurrido un error interno. Intenta nuevamente."}
        return jsonify(payload), 500


def _build_payload(default_message: str, exc: Any) -> Dict[str, Any]:
    description = getattr(exc, "description", None)
    message = getattr(exc, "message", None)
    text = None
    for value in (description, message, str(exc)):
        if value:
            text = str(value)
            break
    if text is None or text == default_message:
        text = default_message
    return {"error": text}
