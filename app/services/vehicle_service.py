from __future__ import annotations

"""Capa de servicios que encapsula la logica de vehiculos."""

import mimetypes
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, List, Optional, Sequence
from uuid import uuid4

from flask import current_app
from werkzeug.datastructures import FileStorage

from app.extensions import supabase_client
from app.models import Vehicle
from app.repositories import ReservationRepository, VehicleRepository


class VehicleService:
    """Coordina las operaciones relacionadas con vehiculos."""

    STATUS_ACTIVE = "activo"
    STATUS_INACTIVE = "inactivo"
    DEFAULT_CURRENCY = "USD"
    ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png"}
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}
    LICENSE_PLATE_REGEX = re.compile(r"^[A-Z]{3}\d{2}[A-Z0-9]$|^[A-Z]{3}\d{3}$")

    def __init__(
        self,
        repository: VehicleRepository | None = None,
        reservation_repository: ReservationRepository | None = None,
    ) -> None:
        self._vehicle_repository = repository or VehicleRepository()
        self._reservation_repository = reservation_repository or ReservationRepository()

    # -------------------------------------------------------------------------
    # Consultas publicas
    # -------------------------------------------------------------------------
    def get_vehicle(self, vehicle_id: str, *, include_inactive: bool = False) -> Optional[Vehicle]:
        record = self._vehicle_repository.get_by_id(vehicle_id)
        if record is None:
            return None
        if not include_inactive and record.get("status") != self.STATUS_ACTIVE:
            return None
        return Vehicle(**record)

    def buscar_vehiculos(
        self,
        *,
        ciudad: Optional[str] = None,
        tipo: Optional[str] = None,
        precio_min: Optional[float] = None,
        precio_max: Optional[float] = None,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, object]:
        requiere_disponibilidad = fecha_inicio is not None and fecha_fin is not None

        if requiere_disponibilidad:
            response = self._vehicle_repository.search(
                ciudad=ciudad,
                tipo=tipo,
                precio_min=precio_min,
                precio_max=precio_max,
                status=self.STATUS_ACTIVE,
                limit=None,
                offset=0,
            )
        else:
            response = self._vehicle_repository.search(
                ciudad=ciudad,
                tipo=tipo,
                precio_min=precio_min,
                precio_max=precio_max,
                status=self.STATUS_ACTIVE,
                limit=limit,
                offset=offset,
                include_count=True,
            )

        data = getattr(response, "data", None) or []
        vehiculos = [Vehicle(**item) for item in data]

        if requiere_disponibilidad and vehiculos:
            vehiculos_disponibles = self._filtrar_por_disponibilidad(vehiculos, fecha_inicio, fecha_fin)
            total = len(vehiculos_disponibles)
            items = vehiculos_disponibles[offset : offset + limit]
        else:
            total = getattr(response, "count", len(vehiculos)) or len(vehiculos)
            items = vehiculos

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def listar_ciudades(self) -> List[str]:
        try:
            return self._vehicle_repository.listar_ciudades()
        except Exception as exc:  # pragma: no cover - devuelve error generico
            raise RuntimeError("No pudimos obtener el catalogo de ciudades.") from exc

    # -------------------------------------------------------------------------
    # Operaciones de administracion
    # -------------------------------------------------------------------------
    def registrar_vehiculo(
        self,
        *,
        license_plate: str,
        make: str,
        model: str,
        year: int | str,
        vehicle_type: str,
        price_per_day: float | str,
        location: str,
        descripcion: Optional[str] = None,
        capacity: Optional[int | str] = None,
        owner_id: Optional[str] = None,
        created_by: Optional[str] = None,
        images: Sequence[FileStorage] | None = None,
    ) -> Vehicle:
        datos_config = self._obtener_configuracion()
        min_year = datos_config["min_year"]
        max_image_bytes = datos_config["max_image_bytes"]
        bucket_name = datos_config["bucket"]
        currency = datos_config["currency"]
        if not bucket_name:
            raise RuntimeError("No se ha configurado el bucket de imagenes para vehiculos.")

        vehiculo_data = self._sanear_y_validar_datos(
            license_plate=license_plate,
            make=make,
            model=model,
            year=year,
            vehicle_type=vehicle_type,
            price_per_day=price_per_day,
            location=location,
            descripcion=descripcion,
            capacity=capacity,
            owner_id=owner_id,
            created_by=created_by,
            min_year=min_year,
        )

        imagenes_preparadas = self._preparar_imagenes(images, max_image_bytes)
        if not imagenes_preparadas:
            raise ValueError("Debes adjuntar al menos una imagen en formato JPG o PNG.")

        vehiculo_data["currency"] = currency
        vehiculo_data["status"] = self.STATUS_INACTIVE
        vehiculo_data["images"] = []

        registro = self._vehicle_repository.crear_vehiculo(vehiculo_data)
        vehicle_id = str(registro.get("id"))
        rutas_subidas: list[str] = []

        try:
            # Incluimos el id del creador en la subida de imágenes para que el path
            # respete las políticas de RLS de Supabase. El atributo "created_by"
            # puede estar ausente si no se proporcionó, por lo que pasamos None
            # en ese caso.
            imagenes_registradas = self._subir_imagenes(
                vehicle_id=vehicle_id,
                imagenes=imagenes_preparadas,
                bucket_name=bucket_name,
                user_id=vehiculo_data.get("created_by"),
            )
            rutas_subidas = [imagen["path"] for imagen in imagenes_registradas]

            actualizado = self._vehicle_repository.actualizar_vehiculo(
                vehicle_id,
                {"images": imagenes_registradas},
            )
        except Exception:
            # Rollback best effort
            self._eliminar_imagenes(bucket_name, rutas_subidas)
            self._vehicle_repository.delete({"id": vehicle_id})
            raise

        return Vehicle(**actualizado)

    def listar_admin(
        self,
        *,
        status: Optional[str] = None,
        ciudad: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, object]:
        estado_normalizado = status.lower() if status else None
        if estado_normalizado not in {None, self.STATUS_ACTIVE, self.STATUS_INACTIVE}:
            raise ValueError("El estado proporcionado no es valido.")

        respuesta = self._vehicle_repository.listar_admin(
            status=estado_normalizado,
            ciudad=ciudad,
            limit=limit,
            offset=offset,
        )
        data = getattr(respuesta, "data", None) or []
        items = [Vehicle(**item) for item in data]
        total = getattr(respuesta, "count", len(items)) or len(items)

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def actualizar_estado(
        self,
        vehicle_id: str,
        *,
        estado: str,
        usuario_validador: Optional[str] = None,
    ) -> Vehicle:
        if not vehicle_id:
            raise ValueError("Debes indicar el vehiculo a actualizar.")

        estado_normalizado = estado.strip().lower()
        if estado_normalizado not in {self.STATUS_ACTIVE, self.STATUS_INACTIVE}:
            raise ValueError("El estado solicitado no es valido.")

        payload: dict[str, object] = {"status": estado_normalizado}
        if estado_normalizado == self.STATUS_ACTIVE:
            payload["validated_by"] = usuario_validador
            payload["validated_at"] = datetime.now(timezone.utc).isoformat()
        else:
            payload["validated_by"] = None
            payload["validated_at"] = None

        actualizado = self._vehicle_repository.actualizar_vehiculo(vehicle_id, payload)
        return Vehicle(**actualizado)

    # -------------------------------------------------------------------------
    # Utilidades internas
    # -------------------------------------------------------------------------
    def _filtrar_por_disponibilidad(
        self,
        vehiculos: Iterable[Vehicle],
        fecha_inicio: date,
        fecha_fin: date,
    ) -> List[Vehicle]:
        ids = [vehiculo.id for vehiculo in vehiculos]
        if not ids:
            return []
        respuesta = self._reservation_repository.obtener_reservas_en_rango(ids, fecha_inicio, fecha_fin)
        reservaciones = getattr(respuesta, "data", None) or []

        vehiculos_ocupados = {
            reserva["vehicle_id"]
            for reserva in reservaciones
            if str(reserva.get("status", "")).lower() != "cancelada"
        }
        return [vehiculo for vehiculo in vehiculos if vehiculo.id not in vehiculos_ocupados]

    def _obtener_configuracion(self) -> dict[str, object]:
        try:
            config = current_app.config  # type: ignore[attr-defined]
        except RuntimeError:
            config = {}

        min_year = int(config.get("VEHICLE_MIN_YEAR", 2015))
        max_mb = float(config.get("VEHICLE_IMAGE_MAX_MB", 3))
        bucket = str(config.get("VEHICLE_IMAGE_BUCKET", "vehicle-images")).strip()
        currency = str(config.get("VEHICLE_DEFAULT_CURRENCY", self.DEFAULT_CURRENCY)).strip() or self.DEFAULT_CURRENCY

        return {
            "min_year": min_year,
            "max_image_bytes": int(max_mb * 1024 * 1024),
            "bucket": bucket,
            "currency": currency,
        }

    def _sanear_y_validar_datos(
        self,
        *,
        license_plate: str,
        make: str,
        model: str,
        year: int | str,
        vehicle_type: str,
        price_per_day: float | str,
        location: str,
        descripcion: Optional[str],
        capacity: Optional[int | str],
        owner_id: Optional[str],
        created_by: Optional[str],
        min_year: int,
    ) -> dict[str, object]:
        placa = self._normalizar_placa(license_plate)
        if not placa:
            raise ValueError("La placa del vehiculo es obligatoria.")
        if not self.LICENSE_PLATE_REGEX.match(placa):
            raise ValueError(
                "La placa del vehiculo no cumple con el formato permitido (ej: ABC123 o ABC12D)."
            )

        marca = (make or "").strip()
        modelo = (model or "").strip()
        categoria = (vehicle_type or "").strip()
        ciudad = (location or "").strip()

        if not marca:
            raise ValueError("La marca del vehiculo es obligatoria.")
        if not modelo:
            raise ValueError("El modelo del vehiculo es obligatorio.")
        if not categoria:
            raise ValueError("La categoria del vehiculo es obligatoria.")
        if not ciudad:
            raise ValueError("La ciudad o ubicacion del vehiculo es obligatoria.")

        try:
            year_value = int(year)
        except (TypeError, ValueError):
            raise ValueError("El anio del vehiculo debe ser un numero entero.")

        if year_value < min_year:
            raise ValueError(f"El anio del vehiculo debe ser igual o superior a {min_year}.")

        current_year = datetime.now().year
        if year_value > current_year + 1:
            raise ValueError("El anio del vehiculo no puede superar el proximo anio calendario.")

        try:
            price = Decimal(str(price_per_day))
        except (InvalidOperation, TypeError):
            raise ValueError("El precio debe ser un valor numerico.")

        if price <= 0:
            raise ValueError("El precio debe ser mayor a cero.")

        capacidad_valor: Optional[int]
        if capacity is None or capacity == "":
            capacidad_valor = None
        else:
            try:
                capacidad_valor = int(capacity)
            except (TypeError, ValueError):
                raise ValueError("La capacidad debe ser un numero entero.")
            if capacidad_valor <= 0:
                raise ValueError("La capacidad debe ser mayor a cero.")

        payload: dict[str, object] = {
            "license_plate": placa,
            "make": marca,
            "model": modelo,
            "year": year_value,
            "vehicle_type": categoria,
            "price_per_day": float(price),
            "location": ciudad,
            "description": (descripcion or "").strip() or None,
            "capacity": capacidad_valor,
            "owner_id": owner_id,
            "created_by": created_by or owner_id,
        }

        # Eliminar claves con None para evitar sobreescrituras innecesarias
        return {clave: valor for clave, valor in payload.items() if valor is not None}

    def _preparar_imagenes(
        self,
        imagenes: Sequence[FileStorage] | None,
        max_image_bytes: int,
    ) -> list[dict[str, object]]:
        if not imagenes:
            return []

        preparadas: list[dict[str, object]] = []
        for archivo in imagenes:
            if archivo is None:
                continue
            nombre_original = (archivo.filename or "").strip()
            if not nombre_original:
                continue

            extension = self._resolver_extension(nombre_original, archivo.mimetype)
            if extension not in self.ALLOWED_IMAGE_EXTENSIONS:
                raise ValueError("Solo se permiten imagenes en formato JPG o PNG.")

            mimetype = archivo.mimetype or mimetypes.guess_type(nombre_original, strict=False)[0] or ""
            mimetype = mimetype.lower()
            if mimetype not in self.ALLOWED_IMAGE_MIME_TYPES:
                raise ValueError("Solo se permiten imagenes en formato JPG o PNG.")

            data = archivo.read()
            if hasattr(archivo, "stream"):
                archivo.stream.seek(0)

            if len(data) == 0:
                raise ValueError("Una de las imagenes adjuntas esta vacia.")
            if len(data) > max_image_bytes:
                limite_mb = max_image_bytes / (1024 * 1024)
                limite_legible = f"{limite_mb:.1f}".rstrip("0").rstrip(".")
                if not limite_legible:
                    limite_legible = "0.1"
                raise ValueError(f"Cada imagen debe pesar maximo {limite_legible}MB.")

            preparadas.append(
                {
                    "original_name": nombre_original,
                    "content_type": mimetype,
                    "extension": extension,
                    "data": data,
                }
            )

        return preparadas

    def _resolver_extension(self, filename: str, mimetype: Optional[str]) -> str:
        extension = Path(filename).suffix.lower().lstrip(".")
        if extension in self.ALLOWED_IMAGE_EXTENSIONS:
            return extension
        if mimetype:
            guessed = mimetypes.guess_extension(mimetype, strict=False)
            if guessed:
                guessed = guessed.lstrip(".").lower()
                if guessed in self.ALLOWED_IMAGE_EXTENSIONS:
                    return guessed
        return extension

    def _subir_imagenes(
        self,
        *,
        vehicle_id: str,
        imagenes: Sequence[dict[str, object]],
        bucket_name: str,
        user_id: Optional[str] = None,
    ) -> list[dict[str, object]]:
        if not supabase_client.is_initialized:
            raise RuntimeError(
                "El cliente de Supabase no esta inicializado. Configura las credenciales antes de subir imagenes."
            )

        storage = supabase_client.client.storage
        bucket = storage.from_(bucket_name)

        registros: list[dict[str, object]] = []
        rutas: list[str] = []

        for indice, imagen in enumerate(imagenes, start=1):
            extension = str(imagen["extension"])
            content_type = str(imagen["content_type"])
            nombre_aleatorio = uuid4().hex[:12]
            #
            # Construir la ruta de almacenamiento respetando las politicas RLS de Supabase.
            # Supabase por defecto suele aplicar una politica donde el nombre del objeto debe
            # comenzar con el identificador del usuario autenticado (auth.uid()). Para cumplir
            # con esta restriccion, incluimos el `user_id` como primer segmento del path
            # siempre que se proporcione. Si no hay `user_id`, usamos solamente `vehicle_id`.
            # La estructura resultante será: `<user_id>/vehicles/<vehicle_id>/<n>_<random>.<ext>`
            # Esto garantiza que la primera carpeta del path corresponde al usuario creador.
            root_segment = user_id or ""
            path_segments = []
            if root_segment:
                path_segments.append(root_segment)
            # Mantener la carpeta "vehicles" para organizar mejor los objetos
            path_segments.extend([
                "vehicles",
                vehicle_id,
                f"{indice:02d}_{nombre_aleatorio}.{extension}",
            ])
            path = "/".join(path_segments)
            data = imagen["data"]

            resultado = bucket.upload(
                path,
                data,  # asegúrate que sea bytes (en tu código ya lo es)
                file_options={
                    "content-type": str(content_type),  # ej: "image/jpeg"
                    "x-upsert": "true",
                    # opcional: "cache-control": "public, max-age=3600"
                },
            )

            error = getattr(resultado, "error", None)
            if error is None and isinstance(resultado, dict):
                error = resultado.get("error")
            if error:
                raise RuntimeError(self._extraer_error(error, "subir la imagen del vehiculo"))

            rutas.append(path)
            public_url = bucket.get_public_url(path)
            registros.append(
                {
                    "url": public_url,
                    "path": path,
                    "content_type": content_type,
                }
            )

        return registros

    def _eliminar_imagenes(self, bucket_name: str, rutas: Sequence[str]) -> None:
        if not rutas:
            return
        if not supabase_client.is_initialized:
            return
        storage = supabase_client.client.storage
        bucket = storage.from_(bucket_name)
        try:
            bucket.remove(list(rutas))
        except Exception:
            # Best effort; si falla no debemos interrumpir el flujo principal.
            pass

    @staticmethod
    def _normalizar_placa(value: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", (value or "").upper())

    @staticmethod
    def _extraer_error(error: object, accion: str) -> str:
        if isinstance(error, dict):
            mensaje = error.get("message") or error.get("msg")
            if mensaje:
                return f"No fue posible {accion}: {mensaje}"
        return f"No fue posible {accion}."
