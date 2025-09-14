# 🛰️ SSTV Ground Station
(Headless Debian)

A fully automated ground station for receiving, decoding, and displaying SSTV images from amateur satellites like the ISS. Runs on a headless Debian system using RTL-SDR, Python, and Flask. 

⚠️ Warning this is working in progress and completely AI generated based on prompts. I am testing and troubleshooting using a Mac Mini 2009 and Debian 12 headless.

## Features

- 📡 Satellite pass prediction via Skyfield
- 🎙️ Automated recording and SSTV decoding
- 🌐 Web interface for control and image gallery
- 🗂️ Metadata archiving for each image
- 🛠️ Cron + `at` scheduling for autonomous operation

## Quick Install

```bash
bash -c "$(curl -fsSL https://github.com/Mraanderson/SSTV-Ground-station-/blob/main/install_sstv_groundstation.sh)"


SSTV-Ground-station/
├── app/                  # Flask web app
│   ├── app.py            # Main Flask app
│   ├── config.json       # User settings
│   ├── templates/        # HTML templates
│   └── static/           # CSS, JS, etc.
├── images/               # SSTV decoded images
├── tle/                  # Satellite TLE files
├── passes/               # Scheduled pass data
├── decoder/              # SSTV decoding logic
├── scripts/              # Utility scripts (e.g. record, schedule)
├── README.md
├── requirements.txt
└── .gitignore
