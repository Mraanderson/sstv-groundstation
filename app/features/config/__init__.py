from flask import Blueprint

# Create the blueprint for the config feature
bp = Blueprint(
    'config',                 # Blueprint name
    __name__,                 # Import name
    template_folder='templates',
    static_folder='static'
)

# Import routes so they are registered with the blueprint
from . import routes

