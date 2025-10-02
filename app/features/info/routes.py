from flask import Blueprint, render_template

bp = Blueprint('info', __name__, template_folder='templates/info')

@bp.route('/info')
def info():
    return render_template('info/info.html')
