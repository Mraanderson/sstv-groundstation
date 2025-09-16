# Remove old folder and pull fresh
rm -rf ~/sstv-groundstation && git clone https://github.com/Mraanderson/sstv-groundstation.git ~/sstv-groundstation

# Go into the project
cd ~/sstv-groundstation

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run the app
python app/app.py
