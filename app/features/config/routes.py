from flask import render_template, current_app
from . import bp
import os
import json

@bp.route("/config", endpoint='config_page')
def config_page():
    config_file = current_app.config['CONFIG_FILE']
    config_data = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception:
            config_data = {"error": "Could not read config file."}
    else:
        config_data = {"message": "No config file found."}

    return render_template("config/config.html", config=config_data)
  
