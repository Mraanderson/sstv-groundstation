# SSTV Groundstation 2.0

A Flask-based web application for managing and displaying decoded SSTV (Slow Scan Television) images, satellite pass predictions, and configuration settings.

---

## 📂 Branch Structure

- **archive-layout** — Frozen copy of the original application layout (read-only reference).
- **main** — Clean slate for the 2.0 rebuild, with modular features and improved structure.

---

## 🗂 Folder Layout

app/
  __init__.py          # App factory and blueprint auto-registration
  config.py            # Central configuration class
  utils/               # Shared utility modules
  features/            # Modular feature blueprints
    gallery/           # Live-updating image gallery
    config/            # Configuration viewer/editor
    passes/            # Satellite pass predictions
    settings/          # Import/export settings
  templates/           # Shared base template
  static/              # Shared static assets
images/                # Decoded SSTV images
tle/                   # Two-Line Element orbital data
run.py                 # App entry point
requirements.txt       # Python dependencies
README.md              # Project documentation

---

## 🚀 Getting Started

### 1. Clone the repository
git clone https://github.com/yourusername/yourrepo.git
cd yourrepo

### 2. Create a virtual environment
python -m venv venv
source venv/bin/activate   # On macOS/Linux
venv\Scripts\activate      # On Windows

### 3. Install dependencies
pip install -r requirements.txt

### 4. Run the application
python run.py

The app will start on http://localhost:5000

---

## 🛠 Features

- **Gallery** — Displays decoded SSTV images with live refresh.
- **Config** — View (and later edit) application configuration.
- **Passes** — Placeholder for satellite pass prediction data.
- **Settings** — Import/export configuration files.

---

## 📌 Notes

- The `images/` and `tle/` folders are tracked with `.gitkeep` so they exist even when empty.
- All features are modular blueprints for easier maintenance and scaling.
- The `archive-layout` branch preserves your old code for reference.

---

## 📜 License

This project is licensed under the MIT License — see the LICENSE file for details.
