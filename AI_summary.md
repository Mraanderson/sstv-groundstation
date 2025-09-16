📡 SSTV Groundstation – AI Context Handover

Overview:
SSTV Groundstation is a Flask-based web application for managing a satellite ground station focused on Slow Scan Television (SSTV) reception. It provides a mobile‑friendly, app‑like interface for:
- Viewing and managing received SSTV images
- Configuring station location and timezone
- Managing and updating satellite TLEs
- Importing and exporting station settings

Key Features:
- Image Gallery: Responsive Bootstrap grid, tap to view full‑size images.
- Station Config: Lat/Lon/Alt/Timezone with Leaflet map, geolocation, altitude API, timezone auto‑detect, form validation.
- Satellite Management: Known SSTV satellites auto‑enabled, refresh list from CelesTrak, enable/disable via checkboxes.
- TLE Viewer: Lists .txt TLE files, last updated timestamp, scrollable content, update all, install cron.
- Import/Export Settings: Upload/download .json config + satellite list.
- UI/UX: Bootstrap 5, dark theme with neon green accents, fixed bottom nav, card‑based layout, touch‑friendly controls.

File Structure (Key Files):
app/
├── app.py                  # Flask app routes and logic
├── templates/
│   ├── base.html           # Shared layout, header, bottom nav
│   ├── gallery.html        # Image gallery
│   ├── config.html         # Station config with map/timezone auto-fill
│   ├── tle_manage.html     # Satellite selection UI
│   ├── tle_view.html       # TLE viewer
│   ├── import_settings.html# Import settings page
│   ├── export_settings.html# Export settings page
images/                     # Received SSTV images
tle/                        # TLE text files
config.json                 # Station config
satellites.json             # Satellite list and settings

Known SSTV Auto‑Enable List:
ISS (ZARYA), ARCTICSAT 1, UMKA 1, SONATE 2, FRAM2HAM

Requirements:
- Python 3.8+
- Flask
- Requests
- Bootstrap 5 (via CDN)
- Leaflet.js (via CDN)

Running the App:
cd app
python3 app.py
Open http://localhost:5000 in your browser.

Recent Changes:
- Mobile‑friendly Bootstrap UI across all pages
- Fixed bottom nav for quick navigation
- Leaflet map + Open‑Elevation API in config page
- Auto‑detect timezone in config page
- Save button validation for config form
- Grouped SSTV satellites at top of /tle/manage
- Dedicated Import and Export pages with consistent styling

Next Steps for Recipient:
To continue development or deployment, please obtain the latest versions of:
- templates/base.html
- app/app.py
directly from the GitHub repository for this project.

These contain the full, runnable code for the UI layout and Flask routes described above. Place them in the correct locations in your local copy of the project.
