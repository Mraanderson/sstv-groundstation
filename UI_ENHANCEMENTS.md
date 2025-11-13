# Manual Recorder UI Enhancement Guide

## Current Status
The manual recorder in `app/features/diagnostics/routes.py` and template `diagnostics/manual_recorder.html` is functional but lacks visibility into:
1. What command will be executed
2. PPM being applied
3. File validation after recording
4. Real-time feedback on recording status

## Recommended Enhancements

### 1. Enhanced Manual Recorder Route (diagnostics/routes.py)

**Add command preview endpoint:**
```python
@bp.route("/recorder/preview", methods=["POST"])
def recorder_preview():
    """Preview the command that will be executed."""
    freq = request.form.get("frequency", "145.800M")
    ppm = int(request.form.get("ppm", get_ppm()))
    duration = int(request.form.get("duration", 30))
    
    from app.utils.sdr_diagnostics import build_rtl_fm_command, build_sox_command
    
    # Parse frequency
    freq_hz = int(float(freq.replace("M", "")) * 1e6)
    
    rtl_cmd = build_rtl_fm_command(freq_hz, ppm, sample_rate=48000, gain=40, duration_s=duration)
    sox_cmd = build_sox_command(48000, "output.wav")
    full_cmd = f"{rtl_cmd} | {sox_cmd}"
    
    return jsonify({
        "frequency_hz": freq_hz,
        "ppm": ppm,
        "duration_s": duration,
        "rtl_fm_command": rtl_cmd,
        "sox_command": sox_cmd,
        "full_command": full_cmd
    })
```

**Enhance POST handler with validation:**
```python
@bp.route("/recorder", methods=["POST"])
def manual_recorder():
    # ... existing code ...
    
    # After successful recording:
    if wav_file.exists():
        from app.utils.sdr_diagnostics import validate_wav_file
        validation = validate_wav_file(wav_file)
        
        if validation["valid"]:
            flash(
                f"✅ Recording OK: {validation['format']}, {validation['duration_s']}s, {validation['size_mb']}MB",
                "success"
            )
        else:
            flash(
                f"⚠️ File created but validation failed: {validation['error']}",
                "warning"
            )
    
    # Continue with soxi analysis & decode...
```

### 2. Enhanced Manual Recorder Template (diagnostics/manual_recorder.html)

**Current template (minimal):**
```html
<form method="post" action="{{ url_for('diagnostics.manual_recorder') }}" class="row g-3 align-items-end mb-4">
    <div class="col-md-3">
        <label for="frequency" class="form-label">Frequency (e.g., 145.800M)</label>
        <input type="text" class="form-control" id="frequency" name="frequency" value="145.800M" required>
    </div>
    <div class="col-md-3">
        <label for="duration" class="form-label">Duration (seconds)</label>
        <input type="number" class="form-control" id="duration" name="duration" value="30" required>
    </div>
    <div class="col-md-3">
        <label for="ppm" class="form-label">PPM Correction</label>
        <input type="number" class="form-control" id="ppm" name="ppm" value="{{ ppm }}" required>
    </div>
    <div class="col-md-3">
        <button type="button" class="btn btn-info" id="previewBtn">👁️ Preview Command</button>
        <button type="submit" class="btn btn-primary">🎙️ Record</button>
    </div>
</form>
```

**Enhanced template with command preview:**
```html
<div class="card mb-4">
    <div class="card-header">
        <h5 class="mb-0">🎙️ Manual Recorder</h5>
    </div>
    <div class="card-body">
        <form method="post" action="{{ url_for('diagnostics.manual_recorder') }}" id="recorderForm">
            <div class="row g-3 mb-3">
                <div class="col-md-3">
                    <label for="frequency" class="form-label">Frequency (MHz)</label>
                    <input type="text" class="form-control" id="frequency" name="frequency" 
                           value="145.800M" placeholder="145.800M" required>
                    <small class="text-muted">e.g., 145.800M or 420.0M</small>
                </div>
                <div class="col-md-2">
                    <label for="duration" class="form-label">Duration (s)</label>
                    <input type="number" class="form-control" id="duration" name="duration" 
                           value="30" min="5" max="1800" required>
                </div>
                <div class="col-md-2">
                    <label for="ppm" class="form-label">PPM Correction</label>
                    <input type="number" class="form-control" id="ppm" name="ppm" 
                           value="{{ ppm }}" readonly>
                    <small class="text-muted d-block mt-1">From calibration</small>
                </div>
                <div class="col-md-5">
                    <label class="form-label d-block mb-2">&nbsp;</label>
                    <button type="button" class="btn btn-sm btn-info me-2" id="previewBtn" onclick="showPreview()">
                        👁️ Preview
                    </button>
                    <button type="submit" class="btn btn-sm btn-primary" onclick="startRecording()">
                        🎙️ Start Recording
                    </button>
                </div>
            </div>

            <!-- Command Preview -->
            <div id="commandPreview" class="alert alert-secondary d-none mb-3">
                <h6>📋 Command Preview:</h6>
                <pre id="previewCommand" style="max-height: 150px; overflow-y: auto;"><code></code></pre>
                <button type="button" class="btn btn-sm btn-outline-secondary mt-2" 
                        onclick="copyCommand()">📋 Copy</button>
            </div>

            <!-- Recording Status -->
            <div id="recordingStatus" class="d-none">
                <div class="progress">
                    <div id="progressBar" class="progress-bar progress-bar-striped progress-bar-animated" 
                         role="progressbar" style="width: 0%">Recording...</div>
                </div>
                <p class="mt-2 text-muted" id="statusText">Waiting to start...</p>
            </div>
        </form>

        <!-- Recent Recordings -->
        <hr>
        <h6>Recent Manual Recordings:</h6>
        <div class="list-group">
            {% for f in files %}
                <a href="{{ url_for('diagnostics.manual_recorder') }}" class="list-group-item list-group-item-action">
                    <div class="d-flex w-100 justify-content-between">
                        <strong>{{ f.name }}</strong>
                        <small>{{ f.stat().st_size | filesizeformat }}</small>
                    </div>
                    <small class="text-muted">{{ f.stat().st_mtime | datetimeformat('%Y-%m-%d %H:%M:%S') }}</small>
                </a>
            {% else %}
                <p class="text-muted">No recordings yet.</p>
            {% endfor %}
        </div>
    </div>
</div>

<script>
function showPreview() {
    const freq = document.getElementById('frequency').value;
    const ppm = document.getElementById('ppm').value;
    const duration = document.getElementById('duration').value;

    fetch('{{ url_for("diagnostics.recorder_preview") }}', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `frequency=${encodeURIComponent(freq)}&ppm=${ppm}&duration=${duration}`
    })
    .then(r => r.json())
    .then(data => {
        const preview = document.getElementById('commandPreview');
        const cmd = document.getElementById('previewCommand').firstChild;
        cmd.textContent = data.full_command;
        preview.classList.remove('d-none');
    })
    .catch(err => alert('Error: ' + err));
}

function copyCommand() {
    const cmd = document.getElementById('previewCommand').textContent;
    navigator.clipboard.writeText(cmd).then(() => {
        alert('Command copied to clipboard');
    });
}

function startRecording() {
    document.getElementById('recordingStatus').classList.remove('d-none');
    document.getElementById('previewCommand').classList.add('d-none');
}
</script>
```

### 3. Add File Size Display Filter

In the template, add a file size filter if not present:

```python
# In app/features/diagnostics/__init__.py or main app
@app.template_filter('filesizeformat')
def filesizeformat(size):
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
```

### 4. Add Real-time Recording Progress

For longer recordings, add AJAX status updates:

```python
@bp.route("/recorder/status", methods=["GET"])
def recorder_status():
    """Check status of ongoing recording."""
    manual_dir = MANUAL_DIR
    latest_wav = None
    for f in sorted(manual_dir.glob("*.wav"), key=os.path.getmtime, reverse=True):
        if f.stat().st_mtime > time.time() - 3600:  # Modified in last hour
            latest_wav = f
            break
    
    if latest_wav:
        try:
            stat = latest_wav.stat()
            from app.utils.sdr_diagnostics import validate_wav_file
            validation = validate_wav_file(latest_wav)
            return jsonify({
                "filename": latest_wav.name,
                "size_mb": round(stat.st_size / (1024*1024), 2),
                "valid": validation["valid"],
                "duration_s": validation.get("duration_s", 0),
                "format": validation.get("format", "Unknown")
            })
        except Exception as e:
            return jsonify({"error": str(e)})
    
    return jsonify({"filename": None})
```

## Key Improvements

✅ **Before:** Users had no visibility into what command was being run  
✅ **After:** Full command preview with exact parameters shown

✅ **Before:** No validation feedback after recording  
✅ **After:** WAV validation status and format info displayed

✅ **Before:** PPM could be wrong with no indication  
✅ **After:** PPM readonly, sourced from calibration, shown prominently

✅ **Before:** Long recordings with no progress feedback  
✅ **After:** Optional AJAX status polling and progress bar

## Priority

1. **High:** Add command preview and validate WAV after recording
2. **Medium:** Make PPM readonly and enhance form layout
3. **Low:** Add progress bar for long recordings
