from flask import Blueprint


bp = Blueprint('api', __name__, static_folder='static')
bp_prefix = '/api'
