from __future__ import annotations

"""Capa de servicios para gestionar reservas de vehiculos."""

from dataclasses import asdict as dataclass_asdict, is_dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable, List, Optional

from app.models import Reservation, Vehicle
from app.repositories import (
    PaymentRepository,
    ReservationRepository,
    VehicleRepository,
)

from .payment_service import PaymentService


class ReservationService:
    """Gestiona la logica de reservas de los usuarios."""

    ESTADO_CONFIRMADA = "confirmada"
    ESTADO_CANCELADA = "cancelada"
    ESTADO_COMPLETADA = "completada"

    def __init__(
        self,
        reservation_repository: ReservationRepository | None = None,
        vehicle_repository: VehicleRepository | None = None,
        payment_service: PaymentService | None = None,
    ) -> None:
        self._reservation_repository = reservation_repository or ReservationRepository()
        self._vehicle_repository = vehicle_repository or VehicleRepository()
        self._payment_service = payment_service or PaymentService(PaymentRepository())

    def listar_reservas(
        self,
        user_id: str,
        *,
        limit: int = 20,
        offset: int = 0,
        rol: Optional[str] = None,
    ) -> dict[str, object]:
        rol_normalizado = (rol or "cliente").strip().lower()
        if rol_normalizado == "administrador":
            response = self._reservation_repository.listar_todas(limit=limit, offset=offset)
        elif rol_normalizado == "anfitrion":
            response = self._reservation_repository.listar_para_anfitrion(user_id, limit=limit, offset=offset)
        else:
            response = self._reservation_repository.listar_por_usuario(user_id, limit=limit, offset=offset)

        data = getattr(response, "data", None) or []
        total = getattr(response, "count", len(data)) or len(data)
        items = []
        for item in data:
            if isinstance(item, dict):
                item_dict = dict(item)
            elif is_dataclass(item):
                item_dict = dataclass_asdict(item)
            else:
                item_dict = dict(item)
            item_dict.pop("vehicles", None)
            items.append(self._convertir_a_modelo(item_dict))

        return {
            "items": items,
            "total": total,
        }

    def crear_reserva(
        self,
        *,
        usuario_id: str,
        vehicle_id: str,
        start_date: str,
        end_date: str,
        comentarios: Optional[str] = None,
        metodo_pago: str = "tarjeta",
        card_last4: Optional[str] = None,
    ) -> dict[str, object]:
        if not vehicle_id:
            raise ValueError("Debes proporcionar el identificador del vehiculo.")
        if not start_date or not end_date:
            raise ValueError("Debes proporcionar las fechas de inicio y fin.")

        fecha_inicio = self._parse_date(start_date)
        fecha_fin = self._parse_date(end_date)
        if fecha_inicio > fecha_fin:
            raise ValueError("La fecha de inicio no puede ser posterior a la fecha final.")

        conflicto = self._reservation_repository.obtener_reservas_en_rango([vehicle_id], fecha_inicio, fecha_fin)
        conflictos = getattr(conflicto, "data", None) or []
        conflictos_filtrados = []
        for item in conflictos:
            if isinstance(item, dict):
                estado = str(item.get("status", "")).lower()
            else:
                estado = str(getattr(item, "status", "")).lower()
            if estado == self.ESTADO_CANCELADA:
                continue
            conflictos_filtrados.append(item)
        if conflictos_filtrados:
            raise ValueError("El vehiculo ya esta reservado en ese rango de fechas.")

        vehiculo = self._vehicle_repository.get_by_id(vehicle_id)
        if vehiculo is None:
            raise ValueError("No se encontro el vehiculo solicitado.")

        vehicle_model = Vehicle(**vehiculo)
        if getattr(vehicle_model, "status", "activo") != "activo":
            raise ValueError("El vehiculo no se encuentra disponible para reservar.")

        dias = (fecha_fin - fecha_inicio).days + 1
        monto = Decimal(str(vehicle_model.price_per_day)) * Decimal(dias)

        payload = {
            "vehicle_id": vehicle_id,
            "user_id": usuario_id,
            "start_date": fecha_inicio.isoformat(),
            "end_date": fecha_fin.isoformat(),
            "status": self.ESTADO_CONFIRMADA,
            "comentarios": comentarios,
        }
        respuesta = self._reservation_repository.crear_reserva(payload)
        datos = getattr(respuesta, "data", None) or []
        if not datos:
            raise RuntimeError("El servicio no devolvio informacion de la reserva creada.")

        reserva = self._convertir_a_modelo(datos[0])
        pago = self._payment_service.procesar_pago(
            reservation_id=reserva.id,
            user_id=usuario_id,
            amount=monto,
            currency=vehicle_model.currency,
            metodo_pago=metodo_pago,
            card_last4=card_last4,
        )

        return {
            "reserva": reserva,
            "pago": pago,
        }

    def cancelar_reserva(self, reserva_id: str, user_id: str, *, is_admin: bool = False) -> Reservation:
        consulta = (
            self._reservation_repository.table()
            .select("*")
            .eq("id", reserva_id)
            .execute()
        )
        data = getattr(consulta, "data", None) or []
        if not data:
            raise ValueError("No se encontro la reserva solicitada.")

        reserva = data[0]
        if not is_admin and reserva.get("user_id") != user_id:
            raise ValueError("No tienes permiso para cancelar esta reserva.")

        if reserva.get("status") != self.ESTADO_CONFIRMADA:
            raise ValueError("Solo es posible cancelar reservas en estado confirmada.")

        self._reservation_repository.cancelar_reserva(reserva_id)
        self._payment_service.marcar_reembolso(reserva_id)
        reserva["status"] = self.ESTADO_CANCELADA
        return self._convertir_a_modelo(reserva)

    def obtener_disponibilidad_vehiculo(
        self,
        vehicle_id: str,
        *,
        incluir_historial: bool = False,
    ) -> list[dict[str, object]]:
        if not vehicle_id:
            raise ValueError("Debes proporcionar el identificador del vehiculo.")

        desde = None if incluir_historial else date.today()
        respuesta = self._reservation_repository.obtener_reservas_de_vehiculo(vehicle_id, desde=desde)
        data = getattr(respuesta, "data", None) or []

        rangos: list[dict[str, object]] = []
        for item in data:
            if not isinstance(item, dict):
                item = dict(item)
            estado = str(item.get("status", "")).lower()
            if estado == self.ESTADO_CANCELADA:
                continue
            inicio = self._parse_date(item.get("start_date"))
            fin = self._parse_date(item.get("end_date"))
            rangos.append(
                {
                    "id": str(item.get("id")),
                    "start_date": inicio.isoformat(),
                    "end_date": fin.isoformat(),
                    "status": estado or self.ESTADO_CONFIRMADA,
                }
            )
        return rangos

    def obtener_reserva_detalle(
        self,
        reserva_id: str,
        usuario_id: str,
        *,
        rol: Optional[str] = None,
        is_admin: bool = False,
    ) -> dict[str, object]:
        if not reserva_id:
            raise ValueError("Debes proporcionar el identificador de la reserva.")

        respuesta = self._reservation_repository.obtener_por_id_con_vehiculo(reserva_id)
        data = getattr(respuesta, "data", None) or []
        if not data:
            raise ValueError("No se encontro la reserva solicitada.")

        registro = data[0]
        if not isinstance(registro, dict):
            registro = dict(registro)

        vehiculo_registro = registro.pop("vehicles", None)
        rol_normalizado = (rol or "").strip().lower()
        es_cliente = registro.get("user_id") == usuario_id
        owner_id = None
        if isinstance(vehiculo_registro, dict):
            owner_id = vehiculo_registro.get("owner_id")
        es_propietario = rol_normalizado == "anfitrion" and owner_id == usuario_id

        if not (es_cliente or is_admin or es_propietario):
            raise ValueError("No tienes permiso para consultar esta reserva.")

        reserva_modelo = self._convertir_a_modelo(registro)
        vehiculo_modelo = None
        if isinstance(vehiculo_registro, dict):
            vehiculo_modelo = Vehicle(**vehiculo_registro)

        return {
            "reserva": reserva_modelo,
            "vehicle": vehiculo_modelo,
        }

    def _convertir_a_modelo(self, registro: dict[str, object]) -> Reservation:
        return Reservation(
            id=str(registro.get("id")),
            vehicle_id=str(registro.get("vehicle_id")),
            user_id=registro.get("user_id"),
            start_date=self._parse_date(registro.get("start_date")),
            end_date=self._parse_date(registro.get("end_date")),
            status=str(registro.get("status") or self.ESTADO_CONFIRMADA),
            created_at=registro.get("created_at"),
            comentarios=registro.get("comentarios"),
        )

    @staticmethod
    def _parse_date(value: object) -> date:
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))
