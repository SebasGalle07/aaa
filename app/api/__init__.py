from flask import Blueprint

api_bp = Blueprint("api", __name__, url_prefix="/api")

from . import auth  # noqa: E402,F401
from . import health  # noqa: E402,F401
from . import vehicles  # noqa: E402,F401
from . import reservations  # noqa: E402,F401
