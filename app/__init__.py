import os
from datetime import datetime
from flask import Flask

def datetimeformat(value, format="%Y-%m-%d %H:%M:%S"):
    """
    Jinja2 filter to format a POSIX timestamp or datetime object.
    """
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value).strftime(format)
    if isinstance(value, datetime):
        return value.strftime(format)
    return str(value)

def create_app():
    app = Flask(__name__)

    # Load config
    app.config.from_object("app.config.Config")

    # Ensure image and TLE directories exist
    os.makedirs(app.config["IMAGE_DIR"], exist_ok=True)
    os.makedirs(app.config["TLE_DIR"], exist_ok=True)

    # Register Jinja2 filters
    app.jinja_env.filters["datetimeformat"] = datetimeformat

    # Auto-discover and register blueprints from features/
    from app import features
    for feature_name in os.listdir(os.path.join(app.root_path, "features")):
        feature_path = os.path.join(app.root_path, "features", feature_name)
        if os.path.isdir(feature_path) and os.path.exists(os.path.join(feature_path, "__init__.py")):
            module = __import__(f"app.features.{feature_name}", fromlist=["bp"])
            if hasattr(module, "bp"):
                app.register_blueprint(module.bp)

    return app
    
