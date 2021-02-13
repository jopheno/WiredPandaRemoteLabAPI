from flask import current_app, request, escape, abort, render_template
from blueprints.home.bp import bp, bp_prefix


@bp.route('/')
def index():
    return render_template('home/index.html')
