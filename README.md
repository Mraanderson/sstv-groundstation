# SSTV Groundstation 2.0

A Flask‑based web application for managing and displaying decoded SSTV (Slow Scan Television) images, satellite pass predictions, and configuration settings. Designed to run on headless Debian systems — tested on Raspberry Pi 3B and Mac Mini 2009 (Debian 12 server). Once launched, the app is managed entirely through a web interface, making it ideal for remote operation and low-power setups.

---

## 🚀 Getting Started

### Option 1 — SSTV Groundstation Launcher (Recommended)

The new `launcher.sh` script replaces the legacy `SSTV.sh` and provides a full-featured interface for managing your SSTV Groundstation install.

#### 🔧 Features

- Switch branches interactively  
- Pull latest updates  
- Backup and restore `images` and `recordings`  
- Run the Flask server locally   

#### 🛠 Setup

Download the launcher script:

```bash
curl -O https://raw.githubusercontent.com/Mraanderson/sstv-groundstation/main/launcher.sh
chmod +x launcher.sh
```

#### 🚀 Usage

Run the launcher interactively:

```bash
./launcher.sh
```

Or use command-line flags:

```bash
./launcher.sh -r            # Run the Flask server
./launcher.sh -u            # Pull latest updates
./launcher.sh -b            # Switch branch
./launcher.sh --backup      # Backup images and recordings
./launcher.sh --restore     # Restore from backup
./launcher.sh --reclone     # Reclone and choose branch
./launcher.sh -p 8080       # Set custom port
./launcher.sh -e production # Set Flask environment
```

The launcher automatically sets up a Python virtual environment and installs dependencies from `requirements.txt`.

---

### Option 2 — Manual Setup

1. **Clone the repository**  
   ```bash
   git clone https://github.com/Mraanderson/sstv-groundstation.git
   cd sstv-groundstation
   ```

2. **Create a virtual environment**  
   ```bash
   python -m venv venv
   ```

3. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**  
   ```bash
   python run.py
   ```

   The app will start on [http://localhost:5000](http://localhost:5000)

---

## 🌐 Web Interface & Remote Management

Once launched, SSTV Groundstation starts a temporary Flask web server on your headless Debian device. This allows full remote management from any browser on the same local network.

For example, if your Raspberry Pi's IP address is `192.168.1.42`, open:

```
http://192.168.1.42:5000
```

in your browser to access the SSTV Groundstation console.

### 🧭 First Steps via Web Console

After launch, use the web interface to:

1. **Set your location** — Required for accurate satellite pass predictions  
2. **Refresh TLE data** — Updates orbital elements for current satellite tracking  
3. **Enable recording** — Starts capturing IQ streams for later decoding  

Captured IQ streams are automatically converted to `.wav` format and added to the **Recordings** library for playback and analysis.

---

## 🛠 Features

- **Gallery** — Displays decoded SSTV images with live refresh  
- **Recordings** — View and play `.wav` files captured from IQ streams  
- **Config** — View and update location/timezone configuration  
- **Passes** — Predicts satellite passes for the next 24 hours  
- **Settings** — Import/export configuration files  
- **Diagnostics** — Check RTL-SDR presence, disk space, and basic system health  

---

## 📌 Notes

- The `images/` folder is tracked with `.gitkeep` so it exists even when empty  
- All features are modular blueprints for easier maintenance and scaling  
- Designed to be contained in a single folder that can be easily removed if no longer required  

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙌 About & Credits

This project has been a true collaboration between:

- **Mraanderson** — The driving force and visionary behind the SSTV Groundstation 2.0 rebuild. Coming into this with little to none Python coding experience, learning everything step‑by‑step, and steering the project’s goals and features  
- **Microsoft Copilot** — Acting as a patient, persistent co‑pilot throughout the build, explaining concepts, writing code, troubleshooting issues, and structuring the project so it’s maintainable and expandable  

From the very first commit to the latest feature, this has been a journey of turning ideas into a working, modular application — proving that with the right guidance, you don’t need to start as a coder to build something powerful.

---

<img width="1915" height="857" alt="image" src="https://github.com/user-attachments/assets/7055340c-1476-4fd4-b925-dcbe472d4514" />
