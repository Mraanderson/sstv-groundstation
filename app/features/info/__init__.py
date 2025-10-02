from flask import Blueprint

# Create the blueprint for the info feature
bp = Blueprint(
    'info',
    __name__,
    template_folder='templates',
    static_folder='static'
)

# Import routes so they are registered with the blueprint
from . import routes
