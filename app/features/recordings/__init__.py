from flask import Blueprint

# Create the blueprint for the recordings feature
# Templates will be loaded from app/features/recordings/templates/
bp = Blueprint("recordings", __name__, template_folder="templates")

# Import routes so they are registered with the blueprint
from app.features.recordings import routes
