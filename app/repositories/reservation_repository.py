from __future__ import annotations

"""Repositorio para gestionar reservas de vehiculos."""

from datetime import date
from typing import Any, Iterable

from .base import SupabaseRepository


class ReservationRepository(SupabaseRepository):
    table_name = "reservations"

    def obtener_reservas_en_rango(
        self,
        vehicle_ids: Iterable[str],
        fecha_inicio: date,
        fecha_fin: date,
    ) -> Any:
        ids = list(vehicle_ids)
        if not ids:
            return []

        query = self.table().select("vehicle_id,start_date,end_date")
        query = query.in_("vehicle_id", ids)
        query = query.lte("start_date", fecha_fin.isoformat())
        query = query.gte("end_date", fecha_inicio.isoformat())
        return query.execute()

    def obtener_reservas_de_vehiculo(
        self,
        vehicle_id: str,
        *,
        desde: date | None = None,
    ) -> Any:
        query = (
            self.table()
            .select("id,vehicle_id,start_date,end_date,status")
            .eq("vehicle_id", vehicle_id)
            .order("start_date", desc=False)
        )
        if desde is not None:
            query = query.gte("end_date", desde.isoformat())
        return query.execute()

    def obtener_por_id_con_vehiculo(self, reserva_id: str) -> Any:
        return (
            self.table()
            .select("*,vehicles(*)")
            .eq("id", reserva_id)
            .execute()
        )

    def listar_por_usuario(self, user_id: str, *, limit: int = 20, offset: int = 0) -> Any:
        query = (
            self.table()
            .select("*", count="exact")
            .eq("user_id", user_id)
            .order("start_date", desc=False)
        )
        return self._apply_pagination(query, limit, offset)

    def listar_para_anfitrion(self, owner_id: str, *, limit: int = 20, offset: int = 0) -> Any:
        query = (
            self.table()
            .select("*,vehicles!inner(owner_id)", count="exact")
            .eq("vehicles.owner_id", owner_id)
            .order("start_date", desc=False)
        )
        return self._apply_pagination(query, limit, offset)

    def listar_todas(self, *, limit: int = 20, offset: int = 0) -> Any:
        query = self.table().select("*", count="exact").order("start_date", desc=False)
        return self._apply_pagination(query, limit, offset)

    def crear_reserva(self, payload: dict[str, Any]) -> Any:
        return self.table().insert(payload).execute()

    def cancelar_reserva(self, reserva_id: str) -> Any:
        return self.table().update({"status": "cancelada"}).eq("id", reserva_id).execute()

    def _apply_pagination(self, query, limit: int, offset: int) -> Any:
        if offset:
            query = query.range(offset, offset + limit - 1)
        else:
            query = query.limit(limit)
        return query.execute()
