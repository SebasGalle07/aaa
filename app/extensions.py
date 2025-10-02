from __future__ import annotations

"""Instancias de extensiones de la aplicacion."""

from typing import Any, Optional

try:
    from supabase import Client, create_client
except ImportError:
    Client = Any  # type: ignore
    create_client = None


class SupabaseClient:
    """Contenedor perezoso del cliente de Supabase que se integra con Flask."""

    def __init__(self) -> None:
        self._client: Optional[Client] = None

    def init_app(self, app) -> None:
        """Inicializar el cliente de Supabase usando la configuracion del app de Flask."""
        if create_client is None:
            app.logger.warning("El cliente de Supabase no esta disponible; instala el paquete \"supabase\".")
            return

        url = app.config.get("SUPABASE_URL")
        service_key = app.config.get("SUPABASE_SERVICE_ROLE_KEY")
        anon_key = app.config.get("SUPABASE_ANON_KEY")
        api_key = service_key or anon_key

        if not url or not api_key:
            app.logger.warning("Las credenciales de Supabase no estan completas; el cliente no se inicializo.")
            return

        self._client = create_client(url, api_key)
        app.logger.debug("Cliente de Supabase inicializado correctamente.")

    @property
    def client(self) -> Client:
        if self._client is None:
            raise RuntimeError(
                "Cliente de Supabase no inicializado. Verifica los valores de configuracion de Supabase."
            )
        return self._client

    @property
    def is_initialized(self) -> bool:
        return self._client is not None


supabase_client = SupabaseClient()
