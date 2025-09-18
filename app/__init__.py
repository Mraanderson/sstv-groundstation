import json
from datetime import datetime
from flask import Flask, redirect, url_for
from app.config_paths import CONFIG_FILE  # <-- shared path

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

    # Load user config
    user_cfg = load_user_config()
    app.config.update(
        LATITUDE=user_cfg["latitude"],
        LONGITUDE=user_cfg["longitude"],
        ALTITUDE_M=user_cfg["altitude_m"],
        TIMEZONE=user_cfg["timezone"],
        THEME=user_cfg.get("theme", "auto")
    )

    app.jinja_env.filters["datetimeformat"] = datetimeformat

    app.save_user_config = lambda: save_user_config({
        "latitude": app.config["LATITUDE"],
        "longitude": app.config["LONGITUDE"],
        "altitude_m": app.config["ALTITUDE_M"],
        "timezone": app.config["TIMEZONE"],
        "theme": app.config["THEME"]
    })

    from app.features.gallery import bp as gallery_bp
    from app.features.config import bp as config_bp
    from app.features.passes import bp as passes_bp
    from app.features.settings import bp as settings_bp

    app.register_blueprint(gallery_bp, url_prefix="/gallery")
    app.register_blueprint(config_bp, url_prefix="/config")
    app.register_blueprint(passes_bp, url_prefix="/passes")
    app.register_blueprint(settings_bp, url_prefix="/settings")

    @app.route("/")
    def home():
        if not app.config.get("LATITUDE") \
           or not app.config.get("LONGITUDE") \
           or not app.config.get("ALTITUDE_M") \
           or not app.config.get("TIMEZONE"):
            return redirect(url_for("config.config_page"))
        return redirect(url_for("gallery.gallery"))

    return app
    
