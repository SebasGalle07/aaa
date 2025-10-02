from __future__ import annotations

"""Repositorio para gestionar pagos en Supabase."""

from typing import Any, Optional

from .base import SupabaseRepository


class PaymentRepository(SupabaseRepository):
    table_name = "payments"

    def crear_pago(self, payload: dict[str, Any]) -> dict[str, Any]:
        respuesta = self.table().insert(payload).execute()
        error = getattr(respuesta, "error", None)
        if error:
            raise RuntimeError(error.get("message", "No fue posible registrar el pago."))
        datos = getattr(respuesta, "data", None) or []
        if not datos:
            raise RuntimeError("El servicio no devolvio informacion del pago.")
        return datos[0]

    def actualizar_estado(self, pago_id: str, estado: str) -> dict[str, Any]:
        respuesta = self.table().update({"status": estado}).eq("id", pago_id).execute()
        error = getattr(respuesta, "error", None)
        if error:
            raise RuntimeError(error.get("message", "No fue posible actualizar el pago."))
        datos = getattr(respuesta, "data", None) or []
        if not datos:
            raise RuntimeError("El servicio no devolvio informacion del pago actualizado.")
        return datos[0]

    def obtener_por_reserva(self, reserva_id: str) -> Optional[dict[str, Any]]:
        respuesta = (
            self.table()
            .select("*")
            .eq("reservation_id", reserva_id)
            .limit(1)
            .execute()
        )
        datos = getattr(respuesta, "data", None)
        if datos:
            return datos[0]
        return None
