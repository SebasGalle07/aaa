from __future__ import annotations

"""Modelo de dominio que representa una reserva de vehiculo."""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(slots=True)
class Reservation:
    id: str
    vehicle_id: str
    user_id: Optional[str]
    start_date: date
    end_date: date
    status: str
    created_at: Optional[str] = None
    comentarios: Optional[str] = None
