from flask import Blueprint

bp = Blueprint('home', __name__, static_folder='static', template_folder='templates')
bp_prefix = '/home'
