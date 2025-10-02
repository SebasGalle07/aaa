from __future__ import annotations

"""Servicios relacionados con la autenticacion de usuarios."""

from dataclasses import asdict
from typing import Dict, Optional

from werkzeug.security import check_password_hash

from app.models import User
from app.repositories import UserRepository
from app.security import create_access_token


class CredencialesInvalidasError(ValueError):
    """Se lanza cuando las credenciales proporcionadas no son validas."""


class AuthService:
    """Gestiona la autenticacion y generacion de tokens."""

    def __init__(self, repository: Optional[UserRepository] = None) -> None:
        self._repository = repository or UserRepository()

    def autenticar(self, email: str, password: str) -> Dict[str, object]:
        """Verificar credenciales y devolver datos y token."""
        if not email or not password:
            raise CredencialesInvalidasError("Debes proporcionar correo y contrasena.")

        registro = self._repository.obtener_por_email(email.lower())
        if not registro or not registro.get("password_hash"):
            raise CredencialesInvalidasError("Credenciales invalidas.")

        if not check_password_hash(registro["password_hash"], password):
            raise CredencialesInvalidasError("Credenciales invalidas.")

        usuario = self._convertir_a_modelo(registro)
        token = create_access_token(
            usuario.id,
            {"email": usuario.email, "rol": usuario.rol},
        )
        payload = asdict(usuario)
        payload["access_token"] = token
        return payload

    def generar_token_para_usuario(self, usuario: User) -> str:
        return create_access_token(
            usuario.id,
            {"email": usuario.email, "rol": usuario.rol},
        )

    def _convertir_a_modelo(self, registro: dict[str, object]) -> User:
        return User(
            id=str(registro.get("id")),
            email=str(registro.get("email")),
            rol=str(registro.get("rol")),
            nombre=registro.get("nombre"),
            created_at=registro.get("created_at"),
        )
