# 🛰️ SSTV Ground Station (Headless Debian)

A fully automated ground station for receiving, decoding, and displaying SSTV images from amateur satellites like the ISS. Runs on a headless Debian system using RTL-SDR, Python, and Flask.

## Features

- 📡 Satellite pass prediction via Skyfield
- 🎙️ Automated recording and SSTV decoding
- 🌐 Web interface for control and image gallery
- 🗂️ Metadata archiving for each image
- 🛠️ Cron + `at` scheduling for autonomous operation

## Quick Install

```bash
bash -c "$(curl -fsSL https://github.com/Mraanderson/SSTV-Ground-station-/blob/main/install_sstv_groundstation.sh)"
