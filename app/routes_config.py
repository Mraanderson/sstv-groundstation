import os, json
from flask import Blueprint, render_template, request
from .utils import CONFIG_FILE, get_timezone_for_coords

bp = Blueprint('config', __name__)

@bp.route("/config", methods=["GET","POST"], endpoint='config_page')
def config_page():
    keys = ["location_lat","location_lon","location_alt","timezone","show_local_time"]
    msg = None
    if request.method=="POST":
        cfg = {k: (request.form.get(k)=="on") if k=="show_local_time" else request.form.get(k,"") for k in keys}
        with open(CONFIG_FILE,"w") as f: json.dump(cfg,f,indent=4)
        msg = "Configuration updated successfully."
    cfg_data = {k:(True if k=="show_local_time" else "") for k in keys}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f: cfg_data = json.load(f)
    return render_template("config.html", config_data=cfg_data, message=msg)

@bp.route("/get-timezone", endpoint='get_timezone')
def get_timezone():
    try:
        lat = float(request.args.get("lat")); lon = float(request.args.get("lon"))
    except (TypeError, ValueError):
        return {"timezone": ""}
    return {"timezone": get_timezone_for_coords(lat, lon)}
    
