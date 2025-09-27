from flask import Blueprint

bp = Blueprint(
    "diagnostics", __name__,
    template_folder="templates",
    static_folder="static"
)

from app.features.diagnostics import routes
