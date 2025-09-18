from flask import render_template, request, redirect, url_for, current_app
from timezonefinder import TimezoneFinder
from . import bp

@bp.route("/", methods=["GET", "POST"], endpoint="config_page")
def config_page():
    if request.method == "POST":
        lat = float(request.form["latitude"])
        lon = float(request.form["longitude"])
        alt = float(request.form["altitude"])

        tf = TimezoneFinder()
        tz = tf.timezone_at(lat=lat, lng=lon)

        current_app.config["LATITUDE"] = lat
        current_app.config["LONGITUDE"] = lon
        current_app.config["ALTITUDE_M"] = alt
        current_app.config["TIMEZONE"] = tz or "UTC"

        current_app.save_user_config()
        return redirect(url_for("config.config_page"))

    return render_template(
        "config/config.html",
        latitude=current_app.config.get("LATITUDE"),
        longitude=current_app.config.get("LONGITUDE"),
        altitude=current_app.config.get("ALTITUDE_M"),
        timezone=current_app.config.get("TIMEZONE")
    )
    
