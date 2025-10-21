"""Decoradores reutilizables para los endpoints de la API."""

from functools import wraps
from typing import Any, Callable, Iterable, TypeVar

from flask import g, jsonify, request

from app.repositories import UserRepository
from app.security import JWTError, decode_token

F = TypeVar("F", bound=Callable[..., Any])


class PermisoDenegadoError(Exception):
    """Se lanza cuando un usuario no posee el rol requerido."""


def require_auth(func: F) -> F:
    """Verificar el encabezado Authorization y adjuntar el usuario a flask.g."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Autenticacion requerida."}), 401

        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return jsonify({"error": "Token no proporcionado."}), 401

        try:
            payload = decode_token(token)
        except JWTError as exc:
            return jsonify({"error": str(exc)}), 401

        user_id = payload.get("sub")
        if not user_id:
            return jsonify({"error": "Token sin identificador de usuario."}), 401

        user_repo = UserRepository()
        try:
            usuario = user_repo.obtener_por_id(user_id)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503
        if usuario is None:
            return jsonify({"error": "Usuario no encontrado."}), 401

        usuario.pop("password_hash", None)
        g.current_user = usuario
        g.current_token_payload = payload

        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def require_roles(*roles: Iterable[str]) -> Callable[[F], F]:
    """Asegurar que el usuario autenticado posee alguno de los roles dados."""

    allowed_roles = {rol.lower() for rol in roles}

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            usuario = getattr(g, "current_user", None)
            if not usuario:
                return jsonify({"error": "Autenticacion requerida."}), 401

            rol_usuario = str(usuario.get("rol", "")).lower()
            if allowed_roles and rol_usuario not in allowed_roles:
                return jsonify({"error": "No tienes permisos para realizar esta accion."}), 403

            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
