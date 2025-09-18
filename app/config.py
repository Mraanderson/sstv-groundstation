import os

class Config:
    # Flask secret key (replace in production)
    SECRET_KEY = os.environ.get("SECRET_KEY", "devkey")

    # Absolute path to decoded images folder
    IMAGE_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'images')
    )

    # Absolute path to TLE data folder
    TLE_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'tle')
    )

    # Path to JSON config file
    CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')
  
