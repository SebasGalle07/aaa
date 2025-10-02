from __future__ import annotations

"""Servicio encargado del flujo de registro de usuarios."""

import re
from typing import Dict, Optional

from werkzeug.security import generate_password_hash

from app.models import User
from app.repositories import UserRepository


class UsuarioExistenteError(ValueError):
    """Se lanza cuando el correo electronico ya se encuentra registrado."""


class DatosInvalidosError(ValueError):
    """Se lanza cuando los datos de entrada no superan la validacion."""


class UserService:
    """Gestiona las operaciones relacionadas con usuarios."""

    CORREO_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    ROLES_DISPONIBLES = {"cliente", "anfitrion", "administrador"}
    ROL_POR_DEFECTO = "cliente"

    def __init__(self, repository: Optional[UserRepository] = None) -> None:
        self._repository = repository or UserRepository()

    def registrar_usuario(
        self,
        nombre: str,
        email: str,
        password: str,
        rol: Optional[str] = None,
    ) -> User:
        datos = self._sanear_datos(nombre=nombre, email=email, password=password, rol=rol)
        self._validar_datos(**datos)

        existente = self._repository.obtener_por_email(datos["email"])
        if existente is not None:
            raise UsuarioExistenteError("Ya existe un usuario con este correo electronico.")

        password_hash = generate_password_hash(datos["password"])
        creado = self._repository.crear_usuario(
            email=datos["email"],
            password_hash=password_hash,
            nombre=datos["nombre"],
            rol=datos["rol"],
        )
        return self._convertir_a_modelo(creado)

    def _convertir_a_modelo(self, registro: Dict[str, object]) -> User:
        return User(
            id=str(registro.get("id")),
            email=str(registro.get("email")),
            rol=str(registro.get("rol") or self.ROL_POR_DEFECTO),
            nombre=registro.get("nombre"),
            created_at=registro.get("created_at"),
        )

    def _sanear_datos(
        self,
        nombre: Optional[str],
        email: Optional[str],
        password: Optional[str],
        rol: Optional[str],
    ) -> Dict[str, str]:
        rol_limpio = (rol or self.ROL_POR_DEFECTO).strip().lower()
        if not rol_limpio:
            rol_limpio = self.ROL_POR_DEFECTO
        return {
            "nombre": (nombre or "").strip(),
            "email": (email or "").strip().lower(),
            "password": password or "",
            "rol": rol_limpio,
        }

    def _validar_datos(self, nombre: str, email: str, password: str, rol: str) -> None:
        errores = []
        if not nombre:
            errores.append("El nombre es obligatorio.")
        if not email:
            errores.append("El correo electronico es obligatorio.")
        elif not self.CORREO_REGEX.match(email):
            errores.append("El correo electronico no tiene un formato valido.")
        if len(password) < 8:
            errores.append("La contrasena debe tener al menos 8 caracteres.")
        if rol not in self.ROLES_DISPONIBLES:
            errores.append(
                "El rol seleccionado no es valido. Roles permitidos: cliente, anfitrion, administrador."
            )

        if errores:
            raise DatosInvalidosError(" ".join(errores))
