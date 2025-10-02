from flask import Blueprint

# Create the blueprint for the passes feature
bp = Blueprint(
    'passes',                 # Blueprint name
    __name__,                 # Import name
    template_folder='templates',
    static_folder='static'
)

# Import routes so they are registered with the blueprint
from . import routes
from . import timeline_api  # Register timeline API endpoints

