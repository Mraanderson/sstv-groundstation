from flask import render_template, request, current_app, jsonify
from timezonefinder import TimezoneFinder
from app.config_paths import CONFIG_FILE
import json
import os
from datetime import datetime
from . import bp

@bp.route("/", methods=["GET", "POST"], endpoint="config_page")
def config_page():
    if request.method == "POST":
        theme = request.form.get("theme", current_app.config.get("THEME", "auto"))

        lat = request.form.get("latitude")
        lon = request.form.get("longitude")
        alt = request.form.get("altitude")
        tz = request.form.get("timezone")

        # Latitude
        if lat not in [None, ""]:
            try:
                current_app.config["LATITUDE"] = float(lat)
            except ValueError:
                return jsonify({"error": "Invalid latitude"}), 400

        # Longitude
        if lon not in [None, ""]:
            try:
                current_app.config["LONGITUDE"] = float(lon)
            except ValueError:
                return jsonify({"error": "Invalid longitude"}), 400

        # Altitude
        if alt not in [None, ""]:
            try:
                current_app.config["ALTITUDE_M"] = float(alt)
            except ValueError:
                return jsonify({"error": "Invalid altitude"}), 400

        # Timezone
        if tz not in [None, ""]:
            current_app.config["TIMEZONE"] = tz
        elif current_app.config.get("LATITUDE") is not None and current_app.config.get("LONGITUDE") is not None:
            tf = TimezoneFinder()
            current_app.config["TIMEZONE"] = tf.timezone_at(
                lat=current_app.config["LATITUDE"],
                lng=current_app.config["LONGITUDE"]
            ) or "UTC"

        # Theme
        current_app.config["THEME"] = theme

        # Save to config file
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        saved = {
            "latitude": current_app.config.get("LATITUDE"),
            "longitude": current_app.config.get("LONGITUDE"),
            "altitude_m": current_app.config.get("ALTITUDE_M"),
            "timezone": current_app.config.get("TIMEZONE"),
            "theme": theme
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(saved, f, indent=2)

        return jsonify({**saved, "saved_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    # GET: load current settings from file if present
    settings = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                settings = json.load(f)
        except Exception:
            settings = {}

    calibrated = "rtl_ppm" in settings

    return render_template(
        "config/config.html",
        latitude=settings.get("latitude"),
        longitude=settings.get("longitude"),
        altitude=settings.get("altitude_m"),
        timezone=settings.get("timezone"),
        settings=settings,
        calibrated=calibrated
    )

@bp.route("/altitude", methods=["GET"])
def get_altitude():
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    if not lat or not lon:
        return jsonify({"error": "Missing coordinates"}), 400

    try:
        import requests
        res = requests.get(f"https://api.opentopodata.org/v1/srtm90m?locations={lat},{lon}")
        data = res.json()
        elevation = data["results"][0]["elevation"]
        return jsonify({"elevation": elevation})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/timezone", methods=["GET"])
def get_timezone():
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    if not lat or not lon:
        return jsonify({"error": "Missing coordinates"}), 400

    try:
        tf = TimezoneFinder()
        tz = tf.timezone_at(lat=float(lat), lng=float(lon)) or "UTC"
        return jsonify({"timezone": tz})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
