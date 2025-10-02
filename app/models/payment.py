from __future__ import annotations

"""Modelo de dominio que representa un pago asociado a una reserva."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(slots=True)
class Payment:
    id: str
    reservation_id: str
    user_id: str
    amount: Decimal
    currency: str
    status: str
    provider: str
    reference: str
    card_last4: Optional[str] = None
    created_at: Optional[str] = None
