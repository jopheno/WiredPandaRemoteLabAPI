from flask import Blueprint, redirect, url_for

bp = Blueprint('index', __name__)


@bp.route("/")
def index():
    return redirect(url_for('home.index'))
