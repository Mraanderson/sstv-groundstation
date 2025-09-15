# SSTV Ground Station

A Python/Flask-based ground station for receiving, decoding, and managing Slow Scan Television (SSTV) images from satellites such as the ISS.  
Includes a web interface for configuration, viewing recent captures, and browsing your full image gallery.

---

## 📂 Project Structure

```
sstv-groundstation/
├── app/                  # Flask web app
│   ├── app.py            # Main Flask application
│   ├── config.json       # User settings
│   └── templates/        # HTML templates
│       ├── config.html   # Configuration page
│       └── gallery.html  # Full gallery page
├── images/               # SSTV decoded images (ignored in Git)
├── passes/               # Scheduled pass data
├── tle/                  # Satellite TLE files
├── decoder/              # SSTV decoding logic
├── scripts/              # Utility scripts
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── .gitignore            # Ignore rules
```

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/Mraanderson/sstv-groundstation.git
cd sstv-groundstation
```

### 2. Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Flask app
```bash
python3 app/app.py
```

By default, the app runs on `http://127.0.0.1:5000`.

---

## ⚙️ Configuration

Edit `app/config.json` to set:
- **Latitude / Longitude / Elevation**
- **Selected satellite**
- **TLE group**
- **Frequency (Hz)**
- **SSTV mode**

---

## 🌐 Web Interface

- **Configuration Page** (`/config`) — adjust station settings and view the latest 8 SSTV images.
- **Gallery Page** (`/gallery`) — browse all decoded SSTV images in `images/`.

---

## 📦 Requirements

Minimal dependencies:
```
flask
requests
```

These are already listed in `requirements.txt`.

---

## 🙌 Credits

This project’s structure, Flask application code, HTML templates, and documentation were developed with the assistance of **Microsoft Copilot**, an AI companion created by Microsoft.  
Copilot provided:
- Full `app.py` with `/config` and `/gallery` routes
- HTML templates for configuration and gallery pages
- Repository structure recommendations
- `.gitignore` and `requirements.txt` setup
- This `README.md` file

---

## 📝 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
