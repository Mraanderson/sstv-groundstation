import os
from datetime import datetime
from flask import render_template, current_app, request, redirect, url_for, send_from_directory
from . import bp

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

def is_image_file(filename):
    return os.path.splitext(filename.lower())[1] in ALLOWED_EXTENSIONS

@bp.route("/", endpoint="gallery")
@bp.route("/gallery", endpoint="gallery")
def gallery():
    image_dir = current_app.config["IMAGE_DIR"]
    images = []

    delete_name = request.args.get("delete")
    if delete_name:
        try:
            os.remove(os.path.join(image_dir, delete_name))
        except OSError:
            pass
        return redirect(url_for("gallery.gallery"))

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

    return render_template("gallery/gallery.html", images=images)

@bp.route("/gallery/image/<path:filename>", endpoint="serve_image")
def serve_image(filename):
    return send_from_directory(current_app.config["IMAGE_DIR"], filename)
