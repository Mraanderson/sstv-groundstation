# SSTV Groundstation — Features Reference

A compact web UI and scheduler for receiving, recording, decoding and browsing SSTV (Slow Scan Television) transmissions. This document summarises the project's current features and where to find them in the repository.

## Core features

- Web UI (Flask) with feature pages:
  - `/info` — Project info, credits, links (ARISS upload guidance included).
  - `/diagnostics` — System checks, RTL-SDR tests, disk/free space, orphan IQ info.
  - `/gallery` — Browse decoded images stored by the app.
  - `/passes` — Orbital pass timeline and current pass info (uses TLEs).
  - `/recordings` — Upload WAVs, view recordings, download logs/metadata.
  - `/config` & `/settings` — Configure observer location, timezone and app settings; import/export.

## SSTV Decoding

- Primary decode via the `sstv` Python package/CLI (installed from `requirements.txt`).
- If decode fails a placeholder image is created so UI remains consistent.
- PD120 fallback integration was removed due to integration issues; PD120 support should be added as an opt-in plugin if required.

## SDR capture and Scheduler

- Uses RTL-SDR (`rtl_sdr`) to capture IQ, converts to WAV with `sox`.
- `sdr_scheduler` schedules passes, marks pass start/end and writes `current_pass.json` to track the active pass.
- Orphan IQ cleanup avoids deleting files during an active pass.

## Recording metadata

- Each recording writes JSON metadata with timestamps, file sizes, satellite info, and decode result.

## TLE and Pass Predictions

- Loads TLEs in `app/static/tle/active.txt` and generates local pass predictions.

## Launcher

- `launcher.sh` provides a simple numeric menu to install, run, update, backup and restore the app (creates/activates venv).
- The launcher activates the venv before checking for Python-installed tools (so `sstv` in venv is detected).

## Key files & locations

- `run.py` — app entrypoint
- `launcher.sh` — simplified CLI launcher/menu
- `requirements.txt` — Python dependencies
- `app/` — main application package
  - `features/` — Blueprints: `gallery`, `passes`, `recordings`, `info`, `diagnostics`, `config`, `settings`
  - `features/*/templates/*` — per-feature templates
  - `utils/` — helpers: `decoder.py`, `sdr_scheduler.py`, `iq_cleanup.py`, `recording_control.py`, `passes.py`, `tle.py`, etc.
- `recordings/` and `images/` — storage for audio, IQ, generated images and metadata
- `~/sstv-groundstation/current_pass.json` — runtime pass state file (written by scheduler)

## Running locally (quick)

1. Create/activate venv and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Start Flask dev server:

```bash
export FLASK_APP=run.py
export FLASK_ENV=development
python -m flask run --host=0.0.0.0 --port=5000
```

Or use `./launcher.sh` for a guided menu.

## Notes & Maintainer Tips

- To clear a stuck pass state, inspect/remove `~/sstv-groundstation/current_pass.json`.
- System deps: `sox` and `rtl_sdr` are required for SDR and audio conversions (apt packages).
- PD120: reintroduce as an opt-in plugin if required.
- Consider adding an admin UI action to safely clear `current_pass.json` and basic unit/smoke tests for core routes.

---

Last updated: 2025-10-02
