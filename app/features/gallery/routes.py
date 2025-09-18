import os
from datetime import datetime
from flask import (
    render_template,
    current_app,
    request,
    redirect,
    url_for,
    send_from_directory
)
from . import bp

# Allowed image extensions (lowercase)
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

def is_image_file(filename):
    """Check if a file has an allowed image extension."""
    return os.path.splitext(filename.lower())[1] in ALLOWED_EXTENSIONS

@bp.route("/", endpoint="gallery")
@bp.route("/gallery", endpoint="gallery")
def gallery():
    image_dir = current_app.config["IMAGE_DIR"]
    images = []

    # Optional delete handling
    delete_name = request.args.get("delete")
    if delete_name:
        try:
            os.remove(os.path.join(image_dir, delete_name))
        except OSError:
            pass
        return redirect(url_for("gallery.gallery"))

    # Walk through all subdirectories
    for root, _, files in os.walk(image_dir):
        for img in sorted(files):
            if is_image_file(img):
                path = os.path.join(root, img)
                rel_path = os.path.relpath(path, image_dir)  # relative to IMAGE_DIR
                images.append({
                    "name": rel_path.replace("\\", "/"),  # Windows-safe
                    "size_kb": round(os.path.getsize(path) / 1024, 1),
                    "modified": datetime.fromtimestamp(os.path.getmtime(path))
                })

    return render_template("gallery/gallery.html", images=images)

@bp.route("/gallery/partial", endpoint="gallery_partial")
def gallery_partial():
    image_dir = current_app.config["IMAGE_DIR"]
    images = []

    for root, _, files in os.walk(image_dir):
        for img in sorted(files):
            if is_image_file(img):
                path = os.path.join(root, img)
                rel_path = os.path.relpath(path, image_dir)
                images.append({
                    "name": rel_path.replace("\\", "/"),
                    "size_kb": round(os.path.getsize(path) / 1024, 1),
                    "modified": datetime.fromtimestamp(os.path.getmtime(path))
                })

    return render_template("gallery/_gallery_items.html", images=images)

@bp.route("/gallery/image/<path:filename>", endpoint="serve_image")
def serve_image(filename):
    """Serve an image from IMAGE_DIR or its subfolders."""
    return send_from_directory(current_app.config["IMAGE_DIR"], filename)
    
