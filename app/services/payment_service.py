from __future__ import annotations

"""Servicios relacionados con pagos simulados dentro de la plataforma."""

from dataclasses import asdict
from decimal import Decimal
from uuid import uuid4
from typing import Optional

from app.models import Payment
from app.repositories import PaymentRepository


class PagoFallidoError(RuntimeError):
    """Se lanza cuando el procesamiento del pago no se completa."""


class PaymentService:
    """Simula el procesamiento de pagos y registro de comprobantes."""

    def __init__(self, repository: Optional[PaymentRepository] = None) -> None:
        self._repository = repository or PaymentRepository()

    def procesar_pago(
        self,
        *,
        reservation_id: str,
        user_id: str,
        amount: Decimal,
        currency: str,
        metodo_pago: str,
        card_last4: Optional[str] = None,
    ) -> Payment:
        if amount <= 0:
            raise PagoFallidoError("El monto a cobrar debe ser mayor que cero.")

        payload = {
            "reservation_id": reservation_id,
            "user_id": user_id,
            "amount": str(amount.quantize(Decimal("0.01"))),
            "currency": currency,
            "status": "pagado",
            "provider": metodo_pago.strip().lower() or "desconocido",
            "reference": f"PAY-{uuid4().hex[:10].upper()}",
            "card_last4": card_last4,
        }

        registro = self._repository.crear_pago(payload)
        return self._convertir_a_modelo(registro)

    def marcar_reembolso(self, reserva_id: str) -> Optional[Payment]:
        pago = self._repository.obtener_por_reserva(reserva_id)
        if not pago:
            return None
        actualizado = self._repository.actualizar_estado(pago["id"], "reembolsado")
        return self._convertir_a_modelo(actualizado)

    def _convertir_a_modelo(self, registro: dict[str, object]) -> Payment:
        return Payment(
            id=str(registro.get("id")),
            reservation_id=str(registro.get("reservation_id")),
            user_id=str(registro.get("user_id")),
            amount=Decimal(str(registro.get("amount"))),
            currency=str(registro.get("currency")),
            status=str(registro.get("status")),
            provider=str(registro.get("provider")),
            reference=str(registro.get("reference")),
            card_last4=registro.get("card_last4"),
            created_at=registro.get("created_at"),
        )
