from __future__ import annotations

"""Endpoints de verificacion de estado."""

from datetime import datetime, UTC
from typing import Any, Dict

from flask import current_app, jsonify

from app.extensions import supabase_client

from . import api_bp


@api_bp.get("/health")
def health_check() -> Any:
    """Probar disponibilidad basica del servicio."""
    response: Dict[str, Any] = {
        "estado": "operativo",
        "marca_de_tiempo": datetime.now(UTC).isoformat(),
        "aplicacion": current_app.config.get("APP_NAME"),
        "entorno": current_app.config.get("FLASK_ENV"),
        "supabase": {
            "configurado": supabase_client.is_initialized,
        },
    }
    return jsonify(response)
