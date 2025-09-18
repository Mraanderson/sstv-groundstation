import os
from datetime import datetime
from flask import render_template, current_app, request, redirect, url_for, send_from_directory
from . import bp

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

    for img in sorted(os.listdir(image_dir)):
        path = os.path.join(image_dir, img)
        if os.path.isfile(path):
            images.append({
                "name": img,
                "size_kb": round(os.path.getsize(path) / 1024, 1),
                "modified": datetime.fromtimestamp(os.path.getmtime(path))
            })

    return render_template("gallery/gallery.html", images=images)

@bp.route("/gallery/partial", endpoint="gallery_partial")
def gallery_partial():
    image_dir = current_app.config["IMAGE_DIR"]
    images = []
    for img in sorted(os.listdir(image_dir)):
        path = os.path.join(image_dir, img)
        if os.path.isfile(path):
            images.append({
                "name": img,
                "size_kb": round(os.path.getsize(path) / 1024, 1),
                "modified": datetime.fromtimestamp(os.path.getmtime(path))
            })
    return render_template("gallery/_gallery_items.html", images=images)

@bp.route("/gallery/image/<path:filename>", endpoint="serve_image")
def serve_image(filename):
    return send_from_directory(current_app.config["IMAGE_DIR"], filename)
    
