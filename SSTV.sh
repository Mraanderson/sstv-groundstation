#!/bin/bash

REPO_URL="https://github.com/Mraanderson/sstv-groundstation.git"
APP_DIR="$HOME/sstv-groundstation"

# Function to clone a specific branch
clone_branch() {
    local branch=$1
    echo "Clearing local folder..."
    rm -rf "$APP_DIR"
    echo "Cloning branch '$branch'..."
    git clone -b "$branch" "$REPO_URL" "$APP_DIR"
}

# Menu
echo "=============================="
echo "   SSTV Groundstation Setup   "
echo "=============================="
echo "1) Clear & clone MAIN branch"
echo "2) Clear & clone TLE branch (tle-expansion)"
echo "3) Clear & clone another branch"
echo "4) Run without git pull"
echo "=============================="
read -p "Select an option: " choice

case $choice in
    1)
        clone_branch "main"
        ;;
    2)
        clone_branch "feature/tle-expansion"
        ;;
    3)
        read -p "Enter branch name: " branch
        clone_branch "$branch"
        ;;
    4)
        echo "Skipping git pull..."
        ;;
    *)
        echo "Invalid choice."
        exit 1
        ;;
esac

# Set up virtual environment
cd "$APP_DIR" || exit
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "No requirements.txt found!"
fi

# Launch the app
echo "Launching Flask app..."
export FLASK_APP=run.py
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000
