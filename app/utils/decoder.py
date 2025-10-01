import subprocess, json, shutil
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from datetime import datetime

# --- Folder paths relative to project root ---
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

def decode_sstv_image(wav_path: Path, output_path: Path):
    """Use minisat to decode SSTV image from WAV."""
    if not shutil.which("minisat"):
        raise RuntimeError("minisat is not installed or not in PATH")
    subprocess.run([
        "minisat", "-i", str(wav_path), "-o", str(output_path)
    ], check=True)
    return output_path

def write_metadata(base_name: str, wav_path: Path, sstv_detected: bool, image_path: Path | None):
    """Write metadata JSON for uploaded audio."""
    meta = {
        "filename": wav_path.name,
        "size_kb": round(wav_path.stat().st_size / 1024, 1),
        "sstv_detected": bool(sstv_detected),
        "callsigns": [],
        "decoded_image": image_path.name if image_path else None,
        "timestamp": datetime.now().isoformat(),
        "source": "user_upload"
    }
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
        try:
            image_path = IMAGES_DIR / f"{base_name}_sstv.png"
            decode_sstv_image(resampled, image_path)
        except Exception as e:
            print(f"⚠️ SSTV decode failed: {e}")
            image_path = None

    meta_path = write_metadata(base_name, wav_path, sstv_detected, image_path)

    print(f"✅ Processed {wav_path.name} — SSTV: {sstv_detected}")
    print(f"📄 Metadata: {meta_path.name}")
    if image_path:
        print(f"🖼️ Image saved: {image_path.name}")
        
