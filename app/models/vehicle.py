from __future__ import annotations

"""Modelo de dominio que representa un vehiculo disponible para alquiler."""

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class Vehicle:
    id: str
    owner_id: Optional[str] = None
    make: str = ""
    model: str = ""
    year: int = 0
    vehicle_type: str = ""
    price_per_day: float = 0.0
    currency: str = "USD"
    description: Optional[str] = None
    location: Optional[str] = None
    capacity: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
