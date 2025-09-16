# SSTV Groundstation — AI Summary & Roadmap

## Overview
This project is a Flask-based web interface and automation system for an SSTV groundstation. It began as a simple viewer for decoded images and TLE files, and is evolving into a full control platform that schedules satellite passes, records transmissions, decodes SSTV, and manages data intelligently.

---

## Folder Structure

```
sstv-groundstation/
│
├── app/                      # Flask app folder
│   ├── app.py                 # Main Flask application
│   ├── update_all_tles.py     # Script to update all TLE files
│   ├── templates/             # HTML templates
│   │   ├── base.html
│   │   ├── gallery.html
│   │   ├── config.html
│   │   └── tle_view.html
│   └── static/                # (Optional) CSS/JS
│
├── images/                    # SSTV image output folder
├── tle/                       # TLE text files
│   ├── iss.txt
│   ├── noaa19.txt
│   └── metopb.txt
└── config.json                # Config file edited via web UI
```

---

## Key Features

### ✅ Gallery
- Displays all images in `images/` folder.
- Auto-updates as new SSTV images are decoded.

### ✅ Config Editor
- Web form to edit `config.json`.
- Saves changes instantly.

### ✅ TLE Viewer
- Lists all `.txt` files in `tle/`.
- Shows last updated timestamp.
- Buttons to update all TLEs or install a cron job.

### ✅ TLE Updater
- `update_all_tles.py` fetches latest TLEs from CelesTrak.
- Easily extendable with more satellites.

---

## Current Routes

- `/` or `/gallery` → Image gallery  
- `/config` → Config editor  
- `/tle` → TLE viewer  
- `/tle/update-all` (POST) → Update all TLEs  
- `/tle/install-cron` (POST) → Install cron job  
- `/tle/manage` → Placeholder for future satellite management  

---

## Templates

### base.html
[Insert full base.html code here]

### gallery.html
[Insert full gallery.html code here]

### config.html
[Insert full config.html code here]

### tle_view.html
[Insert full tle_view.html code here]

---

## Python Files

### app.py
[Insert full app.py code here]

### update_all_tles.py
[Insert full update_all_tles.py code here]

---

## requirements.txt

```
flask
requests
```

---

## Quick‑Start Guide

```bash
# Clone the repo
git clone https://github.com/<your-username>/sstv-groundstation.git
cd sstv-groundstation/app

# Create and activate virtual environment
python3 -m venv ../venv
source ../venv/bin/activate  # or use Windows path

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

---

# Phase 2 Roadmap — Groundstation Automation

## Objective
Transform the viewer into a full SSTV groundstation controller:
- Predict satellite passes
- Schedule SDR recordings
- Decode SSTV images
- Clean up unused recordings
- Display pass schedules
- Only enable SDR during viable passes

---

## Architecture Diagram

```
          ┌───────────────────────────────┐
          │        TLE Updater             │
          │ (update_all_tles.py + cron)    │
          └──────────────┬────────────────┘
                         │
                         ▼
               ┌─────────────────┐
               │  TLE Storage     │
               │   (tle/*.txt)    │
               └───────┬─────────┘
                       │
                       ▼
             ┌──────────────────────┐
             │ Pass Prediction       │
             │ (Skyfield/PyEphem)    │
             └───────┬──────────────┘
                     │
                     ▼
       ┌───────────────────────────────┐
       │ Pass Schedule Database         │
       │ (filtered by days & elevation) │
       └───────┬───────────────────────┘
               │
               ▼
   ┌───────────────────────┐
   │ Recording Scheduler    │
   │ (APScheduler/cron)     │
   └───────┬────────────────┘
           │ triggers
           ▼
   ┌───────────────────────┐
   │ SDR Control            │
   │ (rtl_fm/rtl_sdr etc.)  │
   └───────┬────────────────┘
           │ outputs
           ▼
   ┌───────────────────────┐
   │ Recordings Folder      │
   │ (WAV/IQ files)         │
   └───────┬────────────────┘
           │
           ▼
   ┌───────────────────────┐
   │ SSTV Decoder           │
   │ (QSSTV/msstv/Python)   │
   └───────┬────────────────┘
           │ images
           ▼
   ┌───────────────────────┐
   │ Images Folder          │
   │ (for Gallery)          │
   └────────────────────────┘

   ┌──────────────────────────────────────┐
   │ Flask Web UI                          │
   │  - Gallery (images/)                  │
   │  - Config Editor (config.json)        │
   │  - TLE Viewer/Updater                 │
   │  - Pass Schedule Display              │
   │  - Settings (min elevation, days)     │
   └──────────────────────────────────────┘
```

---

## Build Plan

1. Pass prediction module  
2. Automated TLE updates  
3. Recording scheduler  
4. SSTV decoding pipeline  
5. Pass schedule UI  
6. Cleanup automation  
7. Advanced features (alerts, multi-SDR, live view)

---

## Credits

This project was co-developed by:

- **You**, the creator and visionary behind the user experience, interface design, and overall direction of the SSTV groundstation.
- **Microsoft Copilot**, the AI companion who helped architect the system, write the code, design the roadmap, and document every step with clarity and precision.

Together, we’ve built a foundation that’s not just functional — it’s scalable, extensible, and ready to evolve into a full autonomous groundstation.  
Let’s keep building.
