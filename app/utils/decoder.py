from app.utils.pass_info import get_iss_info_at
from app import config_paths
import subprocess, json
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from datetime import datetime
from pydub import AudioSegment
from PIL import Image, ImageDraw

# --- Folder paths ---
RECORDINGS_DIR = Path("recordings")
IMAGES_DIR = Path("images")

RECORDINGS_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

def resample_wav(input_path: Path, output_path: Path):
    """Resample WAV to 11025 Hz mono for SSTV decoding."""
    subprocess.run([
        "sox", str(input_path),
        "-r", "11025", "-c", "1", str(output_path)
    ], check=True)

def detect_sstv_tone(wav_path: Path) -> bool:
    """Detect SSTV sync tone (~1900 Hz) using FFT."""
    sr, data = wavfile.read(wav_path)
    if data.ndim > 1:
        data = data.mean(axis=1)
    fft = np.abs(np.fft.rfft(data))
    freqs = np.fft.rfftfreq(len(data), 1/sr)
    peak_freq = freqs[np.argmax(fft)]
    return 1850 < peak_freq < 1950

def get_duration_seconds(wav_path: Path) -> float:
    """Return audio duration in seconds."""
    audio = AudioSegment.from_wav(wav_path)
    return round(len(audio) / 1000, 1)

def save_placeholder_image(base_name: str):
    """Create a placeholder SSTV image if decode fails."""
    img = Image.new("RGB", (320, 256), color="black")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "SSTV Detected", fill="white")
    img_path = IMAGES_DIR / f"{base_name}_sstv.png"
    img.save(img_path)
    return img_path

def decode_sstv_image(wav_path: Path, output_path: Path):
    """
    Decode SSTV image using `sstv` CLI. If unsupported VIS, use placeholder image.
    """
    try:
        result = subprocess.run(
            ["sstv", "-d", str(wav_path), "-o", str(output_path)],
            check=True, capture_output=True, text=True
        )
        return output_path
    except subprocess.CalledProcessError as e:
        # SSTV decoder returned a non-zero exit code. Log and fall back to placeholder.
        stderr = e.stderr or ""
        print(f"❌ SSTV decode failed: {e}. stderr: {stderr}")
        return None
    except FileNotFoundError:
        print("❌ `sstv` not found in PATH. Install it in your venv.")
        return None

def write_metadata(base_name: str, wav_path: Path, sstv_detected: bool, image_path: Path | None):
    """Write metadata JSON for uploaded audio."""
    # Try to get config for observer location
    try:
        with open(config_paths.CONFIG_FILE) as f:
            cfg = json.load(f)
        lat = cfg.get("latitude")
        lon = cfg.get("longitude")
        alt = cfg.get("altitude_m", 0)
        tz = cfg.get("timezone", "UTC")
    except Exception:
        lat = lon = alt = tz = None

    # Estimate pass midpoint as image time
    now = datetime.now()
    iss_info = None
    if lat is not None and lon is not None and alt is not None:
        iss_info = get_iss_info_at(now, lat, lon, alt, tz)

    meta = {
        "filename": wav_path.name,
        "size_kb": round(wav_path.stat().st_size / 1024, 1),
        "duration_s": get_duration_seconds(wav_path),
        "sstv_detected": bool(sstv_detected),
        "callsigns": [],
        "decoded_image": image_path.name if image_path else None,
        "timestamp": now.isoformat(),
        "source": "user_upload",
    }
    if iss_info:
        meta["iss_lat"] = iss_info["iss_lat"]
        meta["iss_lon"] = iss_info["iss_lon"]
        meta["iss_alt_km"] = iss_info["iss_alt_km"]
        meta["iss_elev_deg"] = iss_info["iss_elev_deg"]
    meta_path = RECORDINGS_DIR / f"{base_name}.json"
    meta_path.write_text(json.dumps(meta, indent=2))
    return meta_path

def process_uploaded_wav(wav_path: Path):
    """Main entry point: resample, detect SSTV, decode, and log."""
    base_name = wav_path.stem
    resampled = RECORDINGS_DIR / f"{base_name}_11025.wav"
    resample_wav(wav_path, resampled)

    sstv_detected = detect_sstv_tone(resampled)
    image_path = None

    if sstv_detected:
        image_path = IMAGES_DIR / f"{base_name}_sstv.png"
        decoded = decode_sstv_image(resampled, image_path)
        if not decoded:
            image_path = save_placeholder_image(base_name)

    meta_path = write_metadata(base_name, wav_path, sstv_detected, image_path)

    print(f"✅ Processed {wav_path.name} — SSTV: {sstv_detected}")
    print(f"📄 Metadata: {meta_path.name}")
    if image_path:
        print(f"🖼️ Image saved: {image_path.name}")
        
