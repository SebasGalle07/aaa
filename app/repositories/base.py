from __future__ import annotations

"""Utilidades base para interactuar con Supabase."""

from typing import Any, Dict, Iterable, Optional

from app.extensions import supabase_client


class SupabaseRepository:
    """Contenedor de conveniencia para consultar tablas de Supabase."""

    table_name: str

    def __init__(self, table_name: Optional[str] = None) -> None:
        self.table_name = table_name or getattr(self, "table_name", "")
        if not self.table_name:
            raise ValueError("Se debe proporcionar un table_name para SupabaseRepository.")

    @property
    def client(self):
        """Retorna la instancia configurada del cliente de Supabase."""
        return supabase_client.client

    def table(self):
        """Retorna un generador de consultas para la tabla de Supabase."""
        return self.client.table(self.table_name)

    def select(self, columns: str = "*", filters: Optional[Dict[str, Any]] = None) -> Any:
        query = self.table().select(columns)
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        return query.execute()

    def insert(self, payload: Dict[str, Any] | Iterable[Dict[str, Any]]) -> Any:
        return self.table().insert(payload).execute()

    def update(self, payload: Dict[str, Any], filters: Optional[Dict[str, Any]] = None) -> Any:
        query = self.table().update(payload)
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        return query.execute()

    def delete(self, filters: Dict[str, Any]) -> Any:
        query = self.table().delete()
        for key, value in filters.items():
            query = query.eq(key, value)
        return query.execute()
