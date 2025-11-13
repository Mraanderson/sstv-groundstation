# Enhanced Manual Recorder Routes

Add these routes to `app/features/diagnostics/routes.py`:

```python
# ═══════════════════════════════════════════════════════════════════════════
# ADD THESE IMPORTS AT TOP OF FILE (if not already present)
# ═══════════════════════════════════════════════════════════════════════════

import wave  # Add if not present

# ═══════════════════════════════════════════════════════════════════════════
# ADD THIS NEW ROUTE (around line 270, after manual_recorder function)
# ═══════════════════════════════════════════════════════════════════════════

@bp.route("/recorder/preview", methods=["POST"])
def recorder_preview():
    """Preview the command that will be executed."""
    try:
        freq = request.form.get("frequency", "145.800M")
        ppm = int(request.form.get("ppm", get_ppm() or 0))
        duration = int(request.form.get("duration", 30))
        
        from app.utils.sdr_diagnostics import build_rtl_fm_command, build_sox_command
        
        # Parse frequency (handle MHz or Hz)
        freq_str = freq.replace("M", "").replace("MHz", "")
        try:
            freq_hz = int(float(freq_str) * 1e6)
        except ValueError:
            return jsonify({"error": f"Invalid frequency: {freq}"}), 400
        
        rtl_cmd = build_rtl_fm_command(freq_hz, ppm, sample_rate=48000, gain=40, duration_s=duration)
        sox_cmd = build_sox_command(48000, "output.wav")
        full_cmd = f"{rtl_cmd} | {sox_cmd}"
        
        return jsonify({
            "success": True,
            "frequency_hz": freq_hz,
            "frequency_mhz": freq_hz / 1e6,
            "ppm": ppm,
            "duration_s": duration,
            "rtl_fm_command": rtl_cmd,
            "sox_command": sox_cmd,
            "full_command": full_cmd
        })
    except Exception as e:
        current_app.logger.exception("Preview failed")
        return jsonify({"error": str(e), "success": False}), 500


@bp.route("/recorder/status", methods=["GET"])
def recorder_status():
    """Check status of the most recent recording."""
    try:
        manual_dir = MANUAL_DIR
        latest_wav = None
        
        # Find the most recent WAV file
        for f in sorted(manual_dir.glob("*.wav"), key=os.path.getmtime, reverse=True):
            if f.stat().st_mtime > time.time() - 3600:  # Modified in last hour
                latest_wav = f
                break
        
        if latest_wav:
            from app.utils.sdr_diagnostics import validate_wav_file
            validation = validate_wav_file(latest_wav)
            stat = latest_wav.stat()
            
            return jsonify({
                "filename": latest_wav.name,
                "size_mb": round(stat.st_size / (1024*1024), 2),
                "valid": validation["valid"],
                "duration_s": validation.get("duration_s", 0),
                "format": validation.get("format", "Unknown"),
                "error": validation.get("error")
            })
        
        return jsonify({"filename": None})
    except Exception as e:
        current_app.logger.exception("Status check failed")
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════
# ENHANCE EXISTING manual_recorder ROUTE
# ═══════════════════════════════════════════════════════════════════════════

# In the existing @bp.route("/recorder", methods=["POST"]) section,
# after the wav_file is created and subprocess completes, add:

        # Check if file was created
        if wav_file.exists():
            from app.utils.sdr_diagnostics import validate_wav_file
            validation = validate_wav_file(wav_file)
            
            if validation["valid"]:
                flash(
                    f"✅ Recording successful: {validation['format']}, "
                    f"{validation['duration_s']}s, {validation['size_mb']}MB",
                    "success"
                )
                # Log validation to file
                with open(log_file, "a") as lf:
                    lf.write(f"\n✅ WAV Validation: {validation['format']}\n")
                    lf.write(f"✅ Duration: {validation['duration_s']}s\n")
                    lf.write(f"✅ Size: {validation['size_mb']}MB\n")
            else:
                flash(
                    f"⚠️ File created but validation failed: {validation['error']}",
                    "warning"
                )
                with open(log_file, "a") as lf:
                    lf.write(f"\n❌ Validation Error: {validation['error']}\n")
        else:
            flash("❌ Recording file was not created!", "danger")
```

## Integration Points

Insert these at the appropriate locations:

1. **New Import** (top of file): `import wave`
2. **Preview Endpoint** (after `manual_recorder` function, ~line 270)
3. **Status Endpoint** (after preview endpoint)
4. **Enhancement** (inside POST handler of `manual_recorder`, after subprocess completes)

## Key Features

✅ Command preview before execution  
✅ WAV file validation after recording  
✅ Detailed validation feedback  
✅ Real-time status checking  

## API Endpoints Added

- **POST `/diagnostics/recorder/preview`** - Get command preview
  - **Parameters:** frequency, ppm, duration
  - **Returns:** Full command string and components

- **GET `/diagnostics/recorder/status`** - Check last recording status
  - **Returns:** File info and validation results

