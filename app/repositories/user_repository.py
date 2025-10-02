from __future__ import annotations

"""Repositorio para gestionar usuarios en Supabase."""

from typing import Any, Optional

from .base import SupabaseRepository


class UserRepository(SupabaseRepository):
    table_name = "users"

    def crear_usuario(
        self,
        email: str,
        password_hash: str,
        nombre: Optional[str] = None,
        rol: str = "cliente",
    ) -> dict[str, Any]:
        payload = {
            "email": email,
            "password_hash": password_hash,
            "nombre": nombre,
            "rol": rol,
        }
        respuesta = self.insert(payload)
        error = getattr(respuesta, "error", None)
        if error:
            raise RuntimeError(error.get("message", "Error desconocido al crear el usuario."))

        datos = getattr(respuesta, "data", None) or []
        if not datos:
            raise RuntimeError("El servicio no devolvio informacion del usuario creado.")
        return datos[0]

    def obtener_por_email(self, email: str) -> Optional[dict[str, Any]]:
        respuesta = (
            self.table()
                .select("id,email,password_hash,nombre,rol,created_at")
                .eq("email", email)
                .limit(1)
                .execute()
        )
        datos = getattr(respuesta, "data", None)
        if datos:
            return datos[0]
        return None

    def obtener_por_id(self, user_id: str) -> Optional[dict[str, Any]]:
        respuesta = (
            self.table()
                .select("id,email,password_hash,nombre,rol,created_at")
                .eq("id", user_id)
                .limit(1)
                .execute()
        )
        datos = getattr(respuesta, "data", None)
        if datos:
            return datos[0]
        return None
