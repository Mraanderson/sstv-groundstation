from flask import Blueprint

bp = Blueprint(
    "recordings",
    __name__,
    template_folder="templates",
    static_folder="static"
)

from . import routes
