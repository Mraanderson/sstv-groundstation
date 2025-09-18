from flask import render_template, request, redirect, url_for, current_app, flash
from timezonefinder import TimezoneFinder
from app.config_paths import CONFIG_FILE  # <-- shared path
import json
import os
from . import bp

@bp.route("/", methods=["GET", "POST"], endpoint="config_page")
def config_page():
    if request.method == "POST":
        try:
            lat = float(request.form["latitude"])
            lon = float(request.form["longitude"])
            alt = float(request.form["altitude"])
        except (ValueError, KeyError):
            flash("Invalid location data. Please click on the map to set your location.", "danger")
            return redirect(url_for("config.config_page"))

        # Guess timezone from lat/lon
        tf = TimezoneFinder()
        tz = tf.timezone_at(lat=lat, lng=lon) or "UTC"

        # Update app config
        current_app.config["LATITUDE"] = lat
        current_app.config["LONGITUDE"] = lon
        current_app.config["ALTITUDE_M"] = alt
        current_app.config["TIMEZONE"] = tz

        # Persist to shared CONFIG_FILE
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "latitude": lat,
                "longitude": lon,
                "altitude_m": alt,
                "timezone": tz,
                "theme": current_app.config.get("THEME", "auto")
            }, f, indent=2)

        flash("Configuration saved successfully.", "success")
        return redirect(url_for("config.config_page"))

    return render_template(
        "config/config.html",
        latitude=current_app.config.get("LATITUDE"),
        longitude=current_app.config.get("LONGITUDE"),
        altitude=current_app.config.get("ALTITUDE_M"),
        timezone=current_app.config.get("TIMEZONE")
    )
    
