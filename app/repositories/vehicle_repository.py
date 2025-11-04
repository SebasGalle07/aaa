from __future__ import annotations

"""Repositorio para la persistencia de vehiculos utilizando Supabase."""

from typing import Any, Optional

from .base import SupabaseRepository


class VehicleRepository(SupabaseRepository):
    table_name = "vehicles"

    def get_by_id(self, vehicle_id: str) -> Optional[dict[str, Any]]:
        response = self.select(filters={"id": vehicle_id})
        data = getattr(response, "data", None)
        if data:
            return data[0]
        return None

    def search(
        self,
        *,
        ciudad: Optional[str] = None,
        tipo: Optional[str] = None,
        precio_min: Optional[float] = None,
        precio_max: Optional[float] = None,
        status: Optional[str] = "activo",
        limit: Optional[int] = 20,
        offset: int = 0,
        include_count: bool = False,
    ) -> Any:
        if include_count:
            query = self.table().select("*", count="exact")
        else:
            query = self.table().select("*")

        if ciudad:
            query = query.ilike("location", f"%{ciudad}%")
        if tipo:
            query = query.eq("vehicle_type", tipo)
        if precio_min is not None:
            query = query.gte("price_per_day", precio_min)
        if precio_max is not None:
            query = query.lte("price_per_day", precio_max)
        if status is not None:
            query = query.eq("status", status)

        query = query.order("price_per_day")

        if limit is not None:
            if offset:
                query = query.range(offset, offset + limit - 1)
            else:
                query = query.limit(limit)
        return query.execute()

    def listar_ciudades(self) -> list[str]:
        response = self.table().select("location").execute()
        data = getattr(response, "data", None) or []

        ciudades: list[str] = []
        vistos: set[str] = set()

        for item in data:
            valor = item.get("location")
            if not isinstance(valor, str):
                continue
            ciudad = valor.strip()
            if not ciudad:
                continue
            clave = ciudad.lower()
            if clave in vistos:
                continue
            vistos.add(clave)
            ciudades.append(ciudad)

        return sorted(ciudades, key=lambda nombre: nombre.lower())

    def crear_vehiculo(self, payload: dict[str, Any]) -> dict[str, Any]:
        respuesta = self.table().insert(payload).execute()
        return self._obtener_unico(respuesta, "registrar el vehiculo")

    def actualizar_vehiculo(self, vehicle_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        respuesta = self.table().update(payload).eq("id", vehicle_id).execute()
        return self._obtener_unico(respuesta, "actualizar el vehiculo")

    def listar_admin(
        self,
        *,
        status: Optional[str] = None,
        ciudad: Optional[str] = None,
        limit: Optional[int] = 20,
        offset: int = 0,
        include_count: bool = True,
    ) -> Any:
        return self.search(
            status=status,
            ciudad=ciudad,
            limit=limit,
            offset=offset,
            include_count=include_count,
        )

    @staticmethod
    def _obtener_unico(respuesta: Any, accion: str) -> dict[str, Any]:
        error = getattr(respuesta, "error", None)
        if error:
            mensaje = error.get("message") if isinstance(error, dict) else str(error)
            raise RuntimeError(f"No fue posible {accion}: {mensaje}")
        datos = getattr(respuesta, "data", None) or []
        if not datos:
            raise RuntimeError(f"El servicio no devolvio informacion al {accion}.")
        return dict(datos[0])
