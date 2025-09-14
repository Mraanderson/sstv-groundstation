@app.route("/config", methods=["GET", "POST"])
def config():
    cfg = load_config()
    sat_cfg = cfg["satellites"].get(cfg["selected_satellite"], {})
    images = sorted([f for f in os.listdir(IMG_DIR) if f.endswith(".png")], reverse=True)

    if request.method == "POST":
        # Update config from form
        cfg["location"]["lat"] = float(request.form.get("lat", 0))
        cfg["location"]["lon"] = float(request.form.get("lon", 0))
        cfg["location"]["elev_m"] = int(request.form.get("elev_m", 0))
        cfg["selected_satellite"] = request.form.get("satellite", "ISS")
        cfg["sstv_mode"] = request.form.get("sstv_mode", "PD120")

        # Update satellite config
        sat_name = cfg["selected_satellite"]
        cfg["satellites"][sat_name] = {
            "tle_group": request.form.get("tle_group", "stations"),
            "freq_hz": int(request.form.get("freq_hz", 145800000)),
            "nominal_mode": cfg["sstv_mode"]
        }

        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)

        # Optional: trigger pass scheduler
        subprocess.Popen(["python3", os.path.join(ROOT, "scripts/pass_scheduler.py")])

        return redirect("/config")

    return render_template("config.html", cfg=cfg, sat_cfg=sat_cfg, images=images[:8])
  
