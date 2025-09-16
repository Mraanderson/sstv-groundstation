# 📡 SSTV Groundstation — ISS‑Only Checkpoint

## 📌 Current State
- Flask app, ISS‑only mode
- `/passes` route hard‑coded to `"ISS (ZARYA)"`
- Reads station location from `app/config.json`
- Reads TLE from `tle/iss__zarya_.txt` (3‑line format, kept fresh from CelesTrak)
- Uses `EarthSatellite` to avoid `skyfield_data` filename errors
- Max elevation computed from `(sat - observer).at(ti)` to avoid `'rotation_at'` error
- Altitude threshold set to `0.0°` to include low passes
- Bootstrap 5 dark‑themed UI

## 📂 Structure
sstv-groundstation/
- app/
  - app.py — Flask routes: gallery, passes, config, import/export settings
  - templates/
    - base.html — nav bar: Gallery, ISS Passes, Config, Import, Export
    - passes.html — simple table: AOS, LOS, Max Elev, Duration
    - gallery.html, config.html, import_settings.html, export_settings.html
  - config.json — station lat/lon/alt/timezone
- images/ — SSTV images
- tle/
  - iss__zarya_.txt — current ISS TLE

## ✅ Behaviour
- `/passes` lists all ISS passes in next 24 h
- No ignore/record toggles
- No template or Skyfield errors
- Consistent dark UI across pages

## 🚀 Possible Next Steps
- Re‑introduce Record/Ignore toggles with persistence
- Automate RTL‑SDR recording during passes
- Integrate SSTV decoding
- Pass filtering (min elevation, daylight/night)
- Auto‑refresh TLEs
- 
