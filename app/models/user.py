from __future__ import annotations

"""Modelo de dominio que representa a un usuario registrado."""

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class User:
    id: str
    email: str
    rol: str
    nombre: Optional[str] = None
    created_at: Optional[str] = None
