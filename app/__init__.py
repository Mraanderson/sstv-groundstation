import os
import json
from datetime import datetime
from flask import Flask

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "user_config.json")

def load_user_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "latitude": None,
        "longitude": None,
        "altitude_m": None,
        "timezone": None,
        "theme": "auto"
    }

def save_user_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)

def datetimeformat(value, format="%Y-%m-%d %H:%M:%S"):
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value).strftime(format)
    if isinstance(value, datetime):
        return value.strftime(format)
    return str(value)

def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    # Load user config into app.config
    user_cfg = load_user_config()
    app.config.update(
        LATITUDE=user_cfg["latitude"],
        LONGITUDE=user_cfg["longitude"],
        ALTITUDE_M=user_cfg["altitude_m"],
        TIMEZONE=user_cfg["timezone"],
        THEME=user_cfg.get("theme", "auto")
    )

    app.jinja_env.filters["datetimeformat"] = datetimeformat

    # Make save function available
    app.save_user_config = lambda: save_user_config({
        "latitude": app.config["LATITUDE"],
        "longitude": app.config["LONGITUDE"],
        "altitude_m": app.config["ALTITUDE_M"],
        "timezone": app.config["TIMEZONE"],
        "theme": app.config["THEME"]
    })

    # Register blueprints
    for feature_name in os.listdir(os.path.join(app.root_path, "features")):
        feature_path = os.path.join(app.root_path, "features", feature_name)
        if os.path.isdir(feature_path) and os.path.exists(os.path.join(feature_path, "__init__.py")):
            module = __import__(f"app.features.{feature_name}", fromlist=["bp"])
            if hasattr(module, "bp"):
                app.register_blueprint(module.bp)

    return app
    
