from flask import Blueprint, request, abort

bp = Blueprint('admin', __name__, static_folder='static', template_folder='templates')
bp_prefix = '/admin'

def localhost(func):
    def inner(*args, **kwargs):
        ip_address = request.remote_addr
        if ip_address != '127.0.0.1':
            abort(401)

        return func(*args, **kwargs)
    return inner
