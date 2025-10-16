from __future__ import annotations

"""Modulo de configuracion para la aplicacion Flask."""

import os


def _env_bool(name: str, default: bool = False) -> bool:
    """Leer una variable de entorno y convertirla a booleano."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "yes", "y"}


class BaseConfig:
    """Configuracion base compartida entre entornos."""

    APP_NAME = os.getenv("APP_NAME", "AutoShare Backend")
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = _env_bool("FLASK_DEBUG", FLASK_ENV == "development")
    TESTING = False

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_SCHEMA = os.getenv("SUPABASE_SCHEMA", "public")
    SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
    SUPABASE_DB_URL = os.getenv(
        "SUPABASE_DB_URL",
        "postgresql://postgres.aaghcbxleapvrknepntf:123456789@aws-1-us-east-2.pooler.supabase.com:6543/postgres",
    )

    JWT_SECRET = os.getenv("JWT_SECRET") or SUPABASE_JWT_SECRET or "dev-secret-change-me"
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRES_MIN = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MIN", "60"))

    JSON_SORT_KEYS = False


class TestConfig(BaseConfig):
    """Configuracion especifica para pruebas."""

    TESTING = True
    DEBUG = True
    JWT_SECRET = "test-secret"
