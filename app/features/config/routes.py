from flask import render_template, request, redirect, url_for, current_app, flash, jsonify
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

        if lat and lon and alt:
            try:
                lat = float(lat)
                lon = float(lon)
                alt = float(alt)
            except ValueError:
                if request.accept_mimetypes['application/json']:
                    return jsonify({"error": "Invalid location data"}), 400
                flash("Invalid location data.", "danger")
                return redirect(url_for("config.config_page"))

            if not tz:
                tf = TimezoneFinder()
                tz = tf.timezone_at(lat=lat, lng=lon) or "UTC"

            current_app.config["LATITUDE"] = lat
            current_app.config["LONGITUDE"] = lon
            current_app.config["ALTITUDE_M"] = alt
            current_app.config["TIMEZONE"] = tz

        current_app.config["THEME"] = theme

        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "latitude": current_app.config.get("LATITUDE"),
                "longitude": current_app.config.get("LONGITUDE"),
                "altitude_m": current_app.config.get("ALTITUDE_M"),
                "timezone": current_app.config.get("TIMEZONE"),
                "theme": theme
            }, f, indent=2)

        if request.accept_mimetypes['application/json']:
            return jsonify({
                "latitude": current_app.config.get("LATITUDE"),
                "longitude": current_app.config.get("LONGITUDE"),
                "elevation": current_app.config.get("ALTITUDE_M"),
                "timezone": current_app.config.get("TIMEZONE"),
                "theme": theme,
                "saved_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

        flash("Configuration saved successfully.", "success")
        return redirect(url_for("config.config_page"))

    return render_template(
        "config/config.html",
        latitude=current_app.config.get("LATITUDE"),
        longitude=current_app.config.get("LONGITUDE"),
        altitude=current_app.config.get("ALTITUDE_M"),
        timezone=current_app.config.get("TIMEZONE")
    )
    
