# SSTV Groundstation 2.0

A Flask‑based web application for managing and displaying decoded SSTV (Slow Scan Television) images, satellite pass predictions, and configuration settings. CLI for headless Debian devices. 

---

## ⚡ Quick Start

```bash
git clone https://github.com/Mraanderson/sstv-groundstation.git
cd sstv-groundstation
python -m venv venv
pip install -r requirements.txt
python run.py
```
The app will start on [http://localhost:5000](http://localhost:5000)

---

## 📂 Branch Structure

- **archive-layout** — Frozen copy of the original application layout (read‑only reference).  
- **main** — Clean slate for the 2.0 rebuild, with modular features and improved structure.

---

## 🚀 Getting Started

### Option 1 — Manual Setup

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

### Option 2 — SSTV Groundstation Setup Script

The `SSTV.sh` script provides a quick way to set up and run the SSTV Groundstation app on a Debian server or similar environment.

When you run it, you’ll see a menu with three options:

1. **Clear & clone the `main` branch** from GitHub  
2. **Clear & clone from a list of all remote branches** (numbered selection)  
3. **Run from the current folder** (only if it already exists locally)  

After your choice, the script will:

1. Remove the existing local copy (if you chose a clone option)  
2. Clone the selected branch from GitHub (unless you skipped)  
3. Create and activate a Python virtual environment (if not already present)  
4. Install dependencies from `requirements.txt`  
5. Launch the Flask app so it’s accessible on your network  

#### 🛠 How to Use

1. Save the script as `SSTV.sh` in your preferred location.  
2. Make it executable:  
   ```bash
   chmod +x SSTV.sh
   ```  
3. Run it:  
   ```bash
   ./SSTV.sh
   ```  
4. Follow the on‑screen menu to choose your branch or run mode.  

💡 **Tip:** The branch list option is useful if you can’t remember the exact branch name — it will query GitHub and let you pick from the available branches.

---

## 🛠 Features

- **Gallery** — Displays decoded SSTV images with live refresh.  
- **Config** — View and update location/timezone configuration.  
- **Passes** — Satellite pass prediction (placeholder in current build).  
- **Settings** — Import/export configuration files.

---

## 📌 Notes

- The `images/` and `tle/` folders are tracked with `.gitkeep` so they exist even when empty.  
- All features are modular blueprints for easier maintenance and scaling.  
- The `archive-layout` branch preserves your old code for reference.

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙌 About & Credits

This project has been a true collaboration between:

- **Mraanderson** — The driving force and visionary behind the SSTV Groundstation 2.0 rebuild. Coming into this with no coding background, learning everything step‑by‑step, and steering the project’s goals and features.  
- **Microsoft Copilot** — Acting as a patient, persistent co‑pilot throughout the build, explaining concepts, writing code, troubleshooting issues, and structuring the project so it’s maintainable and expandable.  

From the very first commit to the latest feature, this has been a journey of turning ideas into a working, modular application — proving that with the right guidance, you don’t need to start as a coder to build something powerful.
