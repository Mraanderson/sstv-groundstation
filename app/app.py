from flask import Flask, render_template, redirect, url_for
import os

app = Flask(__name__)

# Helper function to get image list
def get_image_list():
    images_dir = os.path.join(app.root_path, 'images')
    if not os.path.exists(images_dir):
        return []
    return sorted(os.listdir(images_dir))

# Root route → show gallery
@app.route("/")
def index():
    return render_template("gallery.html", image_names=get_image_list())

# Optional: keep /gallery route as well
@app.route("/gallery")
def gallery():
    return render_template("gallery.html", image_names=get_image_list())

if __name__ == "__main__":
    # Run on all interfaces so you can access from other devices on your network
    app.run(host="0.0.0.0", port=5000, debug=True)
    
