from flask import Flask
from . import routes_gallery, routes_config, routes_passes, routes_settings

app = Flask(__name__)

# Register blueprints
app.register_blueprint(routes_gallery.bp)
app.register_blueprint(routes_config.bp)
app.register_blueprint(routes_passes.bp)
app.register_blueprint(routes_settings.bp)
