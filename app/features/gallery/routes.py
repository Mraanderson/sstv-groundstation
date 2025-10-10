import os
from datetime import datetime
from flask import render_template, current_app, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename # <-- NEW IMPORT
from . import bp

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

def is_image_file(filename):
    """Checks if a file has an allowed extension."""
    return "." in filename and os.path.splitext(filename.lower())[1] in ALLOWED_EXTENSIONS

@bp.route("/", endpoint="gallery")
@bp.route("/gallery", endpoint="gallery")
def gallery():
    """Renders the main gallery page and handles image deletion."""
    image_dir = current_app.config["IMAGE_DIR"]
    images = []

    # Handle deletion request
    delete_name = request.args.get("delete")
    if delete_name:
        try:
            os.remove(os.path.join(image_dir, delete_name))
            flash(f"Successfully deleted {delete_name}", "success")
        except OSError:
            flash(f"Error: Could not delete {delete_name}", "error")
        # Redirect to clean the URL after deletion
        return redirect(url_for("gallery.gallery"))

    # Gather images for display
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


@bp.route("/upload", methods=["POST"], endpoint="upload_image")
def upload_image():
    """Handles file upload via POST request."""
    # 1. Check if the post request has the file part
    if "file" not in request.files:
        flash("Upload failed: No file part in the request.", "error")
        return redirect(url_for("gallery.gallery"))

    file = request.files["file"]

    # 2. Check if the user selected a file
    if file.filename == "":
        flash("Upload failed: No file selected.", "error")
        return redirect(url_for("gallery.gallery"))

    # 3. Check if the file is allowed and save it
    if file and is_image_file(file.filename):
        # Secure the filename before saving
        filename = secure_filename(file.filename)
        
        # Define the full path to save the file
        save_path = os.path.join(current_app.config["IMAGE_DIR"], filename)
        
        try:
            file.save(save_path)
            flash(f"File **{filename}** successfully uploaded!", "success")
        except Exception as e:
            flash(f"Upload failed due to a server error: {e}", "error")
            
        return redirect(url_for("gallery.gallery"))
    else:
        flash("Upload failed: File type not allowed.", "error")
        return redirect(url_for("gallery.gallery"))


@bp.route("/partial", endpoint="gallery_partial")
def gallery_partial():
    """Return just the gallery items partial for AJAX refresh."""
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
    """Serves the image files from the designated directory."""
    return send_from_directory(current_app.config["IMAGE_DIR"], filename)
    
