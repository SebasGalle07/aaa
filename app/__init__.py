from __future__ import annotations

"""Fabrica de aplicaciones para el backend de alquiler de vehiculos."""

import warnings

from flask import Flask

from . import compat  # noqa: F401
from .api import api_bp
from .config import BaseConfig
from .extensions import supabase_client

warnings.filterwarnings(
    "ignore",
    message="The 'JSON_SORT_KEYS' config key is deprecated and will be removed in Flask 2.3. Set 'app.json.sort_keys' instead.",
    category=DeprecationWarning,
)
warnings.filterwarnings(
    "ignore",
    message="Setting 'json_encoder' on the app or a blueprint is deprecated and will be removed in Flask 2.3. Customize 'app.json' instead.",
    category=DeprecationWarning,
)


def create_app(config_object: type[BaseConfig] = BaseConfig) -> Flask:
    """Crear y configurar la instancia principal de Flask."""
    app = Flask(__name__)
    app.config.from_object(config_object)

    json_sort_keys = app.config.get("JSON_SORT_KEYS", False)
    app.config["JSON_SORT_KEYS"] = json_sort_keys
    app.json.sort_keys = json_sort_keys

    configure_extensions(app)
    register_blueprints(app)

    return app


def configure_extensions(app: Flask) -> None:
    """Inicializar las extensiones de la aplicacion."""
    supabase_client.init_app(app)


def register_blueprints(app: Flask) -> None:
    """Registrar los blueprints de Flask."""
    app.register_blueprint(api_bp)
