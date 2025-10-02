from flask import Blueprint, render_template

# Use the package `templates` folder so the template path `info/info.html` resolves
bp = Blueprint('info', __name__, template_folder='templates')

@bp.route('/info')
def info():
    return render_template('info/info.html')
