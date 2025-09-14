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

## File/folder structure suggestion.

sstv-groundstation/
├── app/                  # Flask web app
│   ├── app.py            # Main Flask application
│   ├── config.json       # User settings
│   ├── templates/        # HTML templates
│   │   ├── config.html
│   │   └── gallery.html
│   └── static/           # CSS, JS, images for the UI
├── images/               # SSTV decoded images (empty in repo, .gitkeep inside)
├── tle/                  # Satellite TLE files
├── passes/               # Scheduled pass data
├── decoder/              # SSTV decoding logic
├── scripts/              # Utility scripts (recording, scheduling, etc.)
├── requirements.txt      # Python dependencies
├── README.md             # Project overview & setup instructions
├── .gitignore            # Ignore rules
└── LICENSE               # License file
