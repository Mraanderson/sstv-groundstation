# Enhanced Manual Recorder HTML Template

Replace the content of `app/features/diagnostics/templates/diagnostics/manual_recorder.html`

with this enhanced version:

```html
{% extends "base.html" %}
{% block title %}Manual Recorder{% endblock %}
{% block content %}

<div class="container my-4">
    <h1 class="mb-4">🎙️ Manual Recorder</h1>

    <div class="card shadow-sm mb-4">
        <div class="card-header bg-primary text-white">
            <h5 class="mb-0">Recording Setup</h5>
        </div>
        <div class="card-body">
            <form method="post" action="{{ url_for('diagnostics.manual_recorder') }}" id="recorderForm" class="needs-validation">
                <div class="row g-3 mb-3">
                    <!-- Frequency Input -->
                    <div class="col-md-3">
                        <label for="frequency" class="form-label">📶 Frequency</label>
                        <input type="text" class="form-control" id="frequency" name="frequency" 
                               value="145.800M" placeholder="145.800M" required>
                        <small class="text-muted d-block mt-1">e.g., 145.800M for ISS</small>
                    </div>

                    <!-- Duration Input -->
                    <div class="col-md-2">
                        <label for="duration" class="form-label">⏱️ Duration (seconds)</label>
                        <input type="number" class="form-control" id="duration" name="duration" 
                               value="30" min="5" max="1800" required>
                        <small class="text-muted d-block mt-1">5-1800 seconds</small>
                    </div>

                    <!-- PPM Correction (Read-only) -->
                    <div class="col-md-2">
                        <label for="ppm" class="form-label">📍 PPM Correction</label>
                        <input type="number" class="form-control" id="ppm" name="ppm" 
                               value="{{ ppm }}" readonly style="background-color: #e9ecef;">
                        <small class="text-muted d-block mt-1">From calibration</small>
                    </div>

                    <!-- Buttons -->
                    <div class="col-md-5">
                        <label class="form-label">&nbsp;</label>
                        <div class="d-flex gap-2">
                            <button type="button" class="btn btn-sm btn-info" id="previewBtn" onclick="showPreview()">
                                👁️ Preview Command
                            </button>
                            <button type="submit" class="btn btn-sm btn-primary" onclick="startRecording()">
                                🎙️ Start Recording
                            </button>
                            <button type="button" class="btn btn-sm btn-secondary" onclick="checkStatus()">
                                ✓ Check Status
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Command Preview (Hidden by default) -->
                <div id="commandPreview" class="alert alert-secondary d-none mb-3">
                    <h6 class="mb-2">📋 Command Preview:</h6>
                    <pre id="previewCommand" style="max-height: 200px; overflow-y: auto; background: #2d2d2d; color: #f8f8f2; padding: 10px; border-radius: 4px;"><code></code></pre>
                    <small class="text-muted">This is the exact command that will be executed.</small>
                    <br>
                    <button type="button" class="btn btn-sm btn-outline-secondary mt-2" onclick="copyCommand()">
                        📋 Copy to Clipboard
                    </button>
                </div>

                <!-- Recording Status (Hidden until recording starts) -->
                <div id="recordingStatus" class="d-none mb-3">
                    <div class="alert alert-info">
                        <h6 class="mb-2">⏳ Recording in progress...</h6>
                        <div class="progress">
                            <div id="progressBar" class="progress-bar progress-bar-striped progress-bar-animated" 
                                 role="progressbar" style="width: 100%"></div>
                        </div>
                        <small id="statusText" class="text-muted d-block mt-2">Please wait for recording to complete...</small>
                    </div>
                </div>

                <!-- File Status (Shows after recording) -->
                <div id="fileStatus" class="d-none mb-3">
                    <div id="statusAlert"></div>
                </div>
            </form>
        </div>
    </div>

    <!-- Recent Recordings -->
    <div class="card shadow-sm">
        <div class="card-header">
            <h5 class="mb-0">📁 Recent Manual Recordings</h5>
        </div>
        <div class="card-body">
            {% if files %}
                <div class="table-responsive">
                    <table class="table table-sm table-hover">
                        <thead class="table-light">
                            <tr>
                                <th>📄 Filename</th>
                                <th>📅 Date/Time</th>
                                <th>💾 Size</th>
                                <th>🔗 Links</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for f in files %}
                                <tr>
                                    <td><code>{{ f.name }}</code></td>
                                    <td>
                                        {% if f.stat().st_mtime %}
                                            <small>{{ f.stat().st_mtime | datetimeformat('%Y-%m-%d %H:%M:%S') }}</small>
                                        {% else %}
                                            <small>N/A</small>
                                        {% endif %}
                                    </td>
                                    <td>
                                        <small>{{ (f.stat().st_size / (1024*1024)) | round(2) }} MB</small>
                                    </td>
                                    <td>
                                        <a href="{{ url_for('diagnostics.manual_recorder') }}" class="btn btn-xs btn-outline-primary" title="Play">
                                            ▶️
                                        </a>
                                        <a href="javascript:validateFile('{{ f.name }}')" class="btn btn-xs btn-outline-info" title="Validate">
                                            ✓
                                        </a>
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            {% else %}
                <p class="text-muted">No recordings yet. Click "Start Recording" to create one.</p>
            {% endif %}
        </div>
    </div>

    <!-- Information Card -->
    <div class="card mt-4 shadow-sm">
        <div class="card-header bg-light">
            <h6 class="mb-0">ℹ️ Tips</h6>
        </div>
        <div class="card-body small">
            <ul class="mb-0">
                <li><strong>PPM Value:</strong> Automatically loaded from SDR calibration. If 0, run calibration first.</li>
                <li><strong>Frequency:</strong> Use 145.800M for ISS. Can use any frequency accessible to RTL-SDR.</li>
                <li><strong>Duration:</strong> Try 30 seconds for testing; use 600+ seconds for full ISS pass.</li>
                <li><strong>Logs:</strong> Check <code>recordings/manual/*.txt</code> for detailed command and error info.</li>
                <li><strong>Validation:</strong> All recordings are validated for format, duration, and integrity.</li>
            </ul>
        </div>
    </div>
</div>

<script>
// Show command preview
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
        if (data.error) {
            alert('Error: ' + data.error);
            return;
        }
        
        const preview = document.getElementById('commandPreview');
        const cmd = document.getElementById('previewCommand').querySelector('code');
        cmd.textContent = data.full_command;
        preview.classList.remove('d-none');
        
        // Scroll to preview
        preview.scrollIntoView({ behavior: 'smooth' });
    })
    .catch(err => alert('Failed to get preview: ' + err));
}

// Copy command to clipboard
function copyCommand() {
    const cmd = document.getElementById('previewCommand').textContent;
    navigator.clipboard.writeText(cmd).then(() => {
        alert('✅ Command copied to clipboard');
    }).catch(err => alert('Failed to copy: ' + err));
}

// Start recording (show status)
function startRecording() {
    document.getElementById('commandPreview').classList.add('d-none');
    document.getElementById('recordingStatus').classList.remove('d-none');
    document.getElementById('fileStatus').classList.add('d-none');
}

// Check status of last recording
function checkStatus() {
    fetch('{{ url_for("diagnostics.recorder_status") }}')
    .then(r => r.json())
    .then(data => {
        const statusDiv = document.getElementById('fileStatus');
        const statusAlert = document.getElementById('statusAlert');
        
        if (!data.filename) {
            statusAlert.innerHTML = '<div class="alert alert-warning">No recent recordings found.</div>';
            statusDiv.classList.remove('d-none');
            return;
        }
        
        let html = `<div class="alert alert-info">
            <h6>📊 Status: ${data.filename}</h6>
            <ul class="mb-0">
                <li><strong>Valid:</strong> ${data.valid ? '✅ Yes' : '❌ No'}</li>
                <li><strong>Format:</strong> ${data.format}</li>
                <li><strong>Duration:</strong> ${data.duration_s}s</li>
                <li><strong>Size:</strong> ${data.size_mb}MB</li>`;
        
        if (data.error) {
            html += `<li><strong>Error:</strong> ${data.error}</li>`;
        }
        
        html += `</ul></div>`;
        statusAlert.innerHTML = html;
        statusDiv.classList.remove('d-none');
    })
    .catch(err => {
        document.getElementById('statusAlert').innerHTML = `<div class="alert alert-danger">Error: ${err}</div>`;
        document.getElementById('fileStatus').classList.remove('d-none');
    });
}

// Validate a specific file
function validateFile(filename) {
    alert('Validation for: ' + filename + '\n(Feature coming soon)');
}
</script>

{% endblock %}
```

## Integration Steps

1. **Locate the file:** `app/features/diagnostics/templates/diagnostics/manual_recorder.html`

2. **Backup original:** Copy current content somewhere safe

3. **Replace entire file** with the code above

4. **Key improvements:**
   - ✅ Command preview before recording
   - ✅ Three buttons: Preview, Record, Check Status
   - ✅ PPM readonly (from calibration)
   - ✅ Frequency with example
   - ✅ Recording status indicator
   - ✅ File validation display
   - ✅ Recent files table
   - ✅ Tips section
   - ✅ JavaScript functions for interactivity

## Required Endpoints

This template needs:
- `recorder_preview` POST endpoint
- `recorder_status` GET endpoint
- (See ENHANCED_ROUTES.md for implementation)

## Features

✅ Responsive design (mobile + desktop)  
✅ Command preview with copy button  
✅ Real-time status checking  
✅ Validation feedback  
✅ File browser  
✅ Help tips  

