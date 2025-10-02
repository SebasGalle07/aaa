from __future__ import annotations

"""Funciones auxiliares para manejar tokens estilo JWT sin dependencias externas."""

import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from flask import current_app


class JWTError(Exception):
    """Error generico para problemas relacionados con JWT."""


def _get_config() -> Dict[str, Any]:
    secret = current_app.config.get("JWT_SECRET")
    if not secret:
        raise JWTError("La configuracion JWT_SECRET no esta definida.")
    algorithm = current_app.config.get("JWT_ALGORITHM", "HS256").upper()
    if algorithm != "HS256":  # pragma: no cover - solo soportamos HS256
        raise JWTError("Solo se admite el algoritmo HS256 en esta implementacion.")
    expires_min = int(current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES_MIN", 60))
    return {"secret": secret, "algorithm": algorithm, "expires_min": expires_min}


def _urlsafe_b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _urlsafe_b64decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(message: bytes, secret: str) -> bytes:
    import hmac
    import hashlib

    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()


def _json_dumps(value: Dict[str, Any]) -> bytes:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def create_access_token(identity: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
    """Generar un token de acceso firmado (HS256)."""
    config = _get_config()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=config["expires_min"])

    header = {"alg": "HS256", "typ": "JWT"}
    payload: Dict[str, Any] = {
        "sub": identity,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    if additional_claims:
        payload.update(additional_claims)

    header_b64 = _urlsafe_b64encode(_json_dumps(header))
    payload_b64 = _urlsafe_b64encode(_json_dumps(payload))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = _urlsafe_b64encode(_sign(signing_input, config["secret"]))
    return f"{header_b64}.{payload_b64}.{signature}"


def decode_token(token: str) -> Dict[str, Any]:
    """Validar firma y expiracion de un token."""
    config = _get_config()

    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise JWTError("Token con formato invalido.") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_signature = _urlsafe_b64encode(_sign(signing_input, config["secret"]))
    if not hmac_compare(signature_b64, expected_signature):
        raise JWTError("El token es invalido.")

    try:
        payload_data = json.loads(_urlsafe_b64decode(payload_b64))
    except json.JSONDecodeError as exc:
        raise JWTError("El token es invalido.") from exc

    exp = payload_data.get("exp")
    if exp is not None:
        exp_dt = datetime.fromtimestamp(int(exp), tz=timezone.utc)
        if datetime.now(timezone.utc) >= exp_dt:
            raise JWTError("El token ha expirado.")

    return payload_data


def hmac_compare(signature_a: str, signature_b: str) -> bool:
    import hmac

    return hmac.compare_digest(signature_a, signature_b)
