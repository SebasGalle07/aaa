from __future__ import annotations

"""Capa de servicios que encapsula la logica de vehiculos y reservas."""

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


class VehicleService:
    """Coordina las operaciones relacionadas con vehiculos."""

    def __init__(
        self,
        repository: VehicleRepository | None = None,
        reservation_repository: ReservationRepository | None = None,
    ) -> None:
        self._vehicle_repository = repository or VehicleRepository()
        self._reservation_repository = reservation_repository or ReservationRepository()

    def get_vehicle(self, vehicle_id: str) -> Optional[Vehicle]:
        record = self._vehicle_repository.get_by_id(vehicle_id)
        if record is None:
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
        response = self._vehicle_repository.search(
            ciudad=ciudad,
            tipo=tipo,
            precio_min=precio_min,
            precio_max=precio_max,
            limit=limit,
            offset=offset,
        )
        data = getattr(response, "data", None) or []
        total = getattr(response, "count", len(data)) or len(data)
        vehiculos = [Vehicle(**item) for item in data]

        if fecha_inicio and fecha_fin and vehiculos:
            vehiculos = self._filtrar_por_disponibilidad(vehiculos, fecha_inicio, fecha_fin)
            total = len(vehiculos)

        return {
            "items": vehiculos,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def _filtrar_por_disponibilidad(
        self,
        vehiculos: Iterable[Vehicle],
        fecha_inicio: date,
        fecha_fin: date,
    ) -> List[Vehicle]:
        ids = [vehiculo.id for vehiculo in vehiculos]
        respuesta = self._reservation_repository.obtener_reservas_en_rango(ids, fecha_inicio, fecha_fin)
        reservaciones = getattr(respuesta, "data", None) or []
        vehiculos_ocupados = {reserva["vehicle_id"] for reserva in reservaciones}

        return [vehiculo for vehiculo in vehiculos if vehiculo.id not in vehiculos_ocupados]


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
        if conflictos:
            raise ValueError("El vehiculo ya esta reservado en ese rango de fechas.")

        vehiculo = self._vehicle_repository.get_by_id(vehicle_id)
        if vehiculo is None:
            raise ValueError("No se encontro el vehiculo solicitado.")

        vehicle_model = Vehicle(**vehiculo)
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

    def _convertir_a_modelo(self, registro: dict[str, object]) -> Reservation:
        return Reservation(
            id=str(registro.get("id")),
            vehicle_id=str(registro.get("vehicle_id")),
            user_id=registro.get("user_id"),
            start_date=self._parse_date(registro.get("start_date")),
            end_date=self._parse_date(registro.get("end_date")),
            status=str(registro.get("status")),
            created_at=registro.get("created_at"),
            comentarios=registro.get("comentarios"),
        )

    @staticmethod
    def _parse_date(value: object) -> date:
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))



