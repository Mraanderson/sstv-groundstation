from flask import Blueprint, render_template, send_from_directory
from .utils import get_all_images, IMAGES_DIR

bp = Blueprint('gallery', __name__)

@bp.route("/", endpoint='gallery')
@bp.route("/gallery", endpoint='gallery')
def gallery():
    return render_template("gallery.html", image_names=get_all_images())

@bp.route("/images/<path:filename>", endpoint='serve_image')
def serve_image(filename):
    return send_from_directory(IMAGES_DIR, filename)
    
