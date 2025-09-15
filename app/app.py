from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)

# Folder where your images are stored
IMAGES_DIR = os.path.join(app.root_path, 'images')

# Helper: recursively get all image paths
def get_all_images():
    image_files = []
    for root, dirs, files in os.walk(IMAGES_DIR):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                # Get relative path from IMAGES_DIR
                rel_dir = os.path.relpath(root, IMAGES_DIR)
                rel_path = os.path.join(rel_dir, file) if rel_dir != '.' else file
                image_files.append(rel_path.replace("\\", "/"))
    return sorted(image_files)

# Serve images from the images folder
@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(IMAGES_DIR, filename)

# Root route → gallery
@app.route("/")
@app.route("/gallery")
def gallery():
    return render_template("gallery.html", image_names=get_all_images())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    
