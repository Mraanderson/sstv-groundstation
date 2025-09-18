import pkgutil
import importlib
from flask import Flask
from .config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Auto-discover and register all blueprints in app/features/*
    package = f"{__name__}.features"
    features_path = app.root_path + '/features'
    for _, feature_name, _ in pkgutil.iter_modules([features_path]):
        module = importlib.import_module(f"{package}.{feature_name}")
        if hasattr(module, 'bp'):
            app.register_blueprint(module.bp)

    return app
  
