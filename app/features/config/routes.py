from flask import render_template, request, redirect, url_for, current_app, flash, jsonify
from timezonefinder import TimezoneFinder
from app.config_paths import CONFIG_FILE
import json
import os
from datetime import datetime
from . import bp   # ✅ Ensure blueprint is imported so @bp.route works

@bp.route("/", methods=["GET", "POST"], endpoint="config_page")
def config_page():
    if request.method == "POST":
        theme = request.form.get("theme", current_app.config.get("THEME", "auto"))

        lat = request.form.get("latitude")
        lon = request.form.get("longitude")
        alt = request.form.get("altitude")
        tz = request.form.get("timezone")

        # Latitude
        if lat:
            try:
                current_app.config["LATITUDE"] = float(lat)
            except ValueError:
                if request.accept_mimetypes['application/json']:
                    return jsonify({"error": "Invalid latitude"}), 400
                flash("Invalid latitude.", "danger")
                return redirect(url_for("config.config_page"))

        # Longitude
        if lon:
            try:
                current_app.config["LONGITUDE"] = float(lon)
            except ValueError:
                if request.accept_mimetypes['application/json']:
                    return jsonify({"error": "Invalid longitude"}), 400
                flash("Invalid longitude.", "danger")
                return redirect(url_for("config.config_page"))

        # Altitude
        if alt:
            try:
                current_app.config["ALTITUDE_M"] = float(alt)
            except ValueError:
                if request.accept_mimetypes['application/json']:
                    return jsonify({"error": "Invalid altitude"}), 400
                flash("Invalid altitude.", "danger")
                return redirect(url_for("config.config_page"))

        # Timezone
        if tz:
            current_app.config["TIMEZONE"] = tz
        elif lat and lon:
            tf = TimezoneFinder()
            current_app.config["TIMEZONE"] = tf.timezone_at(
                lat=current_app.config["LATITUDE"],
                lng=current_app.config["LONGITUDE"]
            ) or "UTC"

        # Theme
        current_app.config["THEME"] = theme

        # Save to config file
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
                "altitude_m": current_app.config.get("ALTITUDE_M"),
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
    
