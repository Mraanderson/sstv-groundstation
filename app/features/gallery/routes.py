from flask import render_template, send_from_directory, current_app, request
from . import bp
from app.utils.images import get_all_images
import os

@bp.route("/", endpoint='gallery')
@bp.route("/gallery", endpoint='gallery')
def gallery():
    image_names = get_all_images(current_app.config['IMAGE_DIR'])
    return render_template("gallery/gallery.html", image_names=image_names)

@bp.route("/images/<path:filename>", endpoint='serve_image')
def serve_image(filename):
    return send_from_directory(current_app.config['IMAGE_DIR'], filename)

@bp.route("/gallery/partial", endpoint='gallery_partial')
def gallery_partial():
    image_names = get_all_images(current_app.config['IMAGE_DIR'])
    return render_template("gallery/_gallery_items.html", image_names=image_names)
  
