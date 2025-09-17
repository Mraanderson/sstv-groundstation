from flask import Blueprint, render_template, send_from_directory
from .utils import get_all_images, IMAGES_DIR

bp = Blueprint('gallery', __name__)

@bp.route("/")
@bp.route("/gallery")
def gallery():
    return render_template("gallery.html", image_names=get_all_images())

@bp.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(IMAGES_DIR, filename)
    
