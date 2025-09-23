from flask import Blueprint

bp = Blueprint("recordings", __name__, template_folder="../../templates/recordings")

from app.features.recordings import routes
