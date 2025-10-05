#!/bin/bash

REPO_URL="https://github.com/Mraanderson/sstv-groundstation.git"
APP_DIR="$HOME/sstv-groundstation"

# Function to switch to a specific branch
switch_branch() {
    local branch=$1
    if [ -d "$APP_DIR/.git" ]; then
        echo "Switching to branch '$branch'..."
        cd "$APP_DIR" && git checkout "$branch" 2>/dev/null || git checkout -b "$branch" origin/"$branch" 2>/dev/null
    else
        echo "Repository not found, cloning branch '$branch'..."
        git clone -b "$branch" "$REPO_URL" "$APP_DIR"
    fi
}

# Function to get current branch
get_current_branch() {
    if [ -d "$APP_DIR/.git" ]; then
        cd "$APP_DIR" && git branch --show-current
    else
        echo "no repo"
    fi
}

# Menu
current_branch=$(get_current_branch)
echo "=============================="
echo "   SSTV Groundstation Setup   "
echo "=============================="
echo "1) Run (current branch $current_branch)"
echo "2) Change to dev branch"
echo "3) Change to main branch"
echo "=============================="
read -p "Select an option: " choice

case $choice in
    1)
        if [ -d "$APP_DIR" ]; then
            echo "Using existing folder: $APP_DIR"
        else
            echo "Error: $APP_DIR does not exist. Please clone first."
            exit 1
        fi
        ;;
    2)
        switch_branch "dev"
        ;;
    3)
        switch_branch "main"
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
