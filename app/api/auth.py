from __future__ import annotations

"""Endpoints de autenticacion y registro."""

from http import HTTPStatus

from flask import jsonify, request

from app.services import (
    AuthService,
    DatosInvalidosError,
    UserService,
    UsuarioExistenteError,
    CredencialesInvalidasError,
)

from . import api_bp


user_service = UserService()
auth_service = AuthService()


@api_bp.post("/auth/register")
def registrar_usuario():
    """Registrar un nuevo usuario solicitando nombre, correo y contrasena."""
    payload = request.get_json(silent=True) or {}
    nombre = payload.get("nombre")
    email = payload.get("email")
    password = payload.get("password")
    rol = payload.get("rol")

    try:
        usuario = user_service.registrar_usuario(
            nombre=nombre,
            email=email,
            password=password,
            rol=rol,
        )
        token = auth_service.generar_token_para_usuario(usuario)
    except DatosInvalidosError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except UsuarioExistenteError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.CONFLICT
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.SERVICE_UNAVAILABLE

    respuesta = {
        "id": usuario.id,
        "email": usuario.email,
        "nombre": usuario.nombre,
        "rol": usuario.rol,
        "creado_en": usuario.created_at,
        "access_token": token,
    }
    return jsonify(respuesta), HTTPStatus.CREATED


@api_bp.post("/auth/login")
def iniciar_sesion():
    """Autenticar a un usuario por correo y contrasena."""
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    password = payload.get("password")

    try:
        resultado = auth_service.autenticar(email=email, password=password)
    except CredencialesInvalidasError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.UNAUTHORIZED
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.SERVICE_UNAVAILABLE

    return jsonify(resultado)
