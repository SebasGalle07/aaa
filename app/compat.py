from __future__ import annotations

"""Compatibilidad con dependencias externas para evitar errores en tiempo de ejecucion."""

try:
    import werkzeug
except ImportError:  # pragma: no cover
    werkzeug = None

if werkzeug is not None and getattr(werkzeug, "__version__", None) is None:
    # Flask 3.0 aun referencia werkzeug.__version__ en el cliente de pruebas.
    # Las versiones recientes de Werkzeug ya no exponen este atributo, asi que fijamos un valor simbolico.
    setattr(werkzeug, "__version__", "0.0")
