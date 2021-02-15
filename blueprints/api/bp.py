from flask import Blueprint, request, abort


bp = Blueprint('api', __name__, static_folder='static')
bp_prefix = '/api'

def localhost(func):
    def inner(*args, **kwargs):
        ip_address = request.remote_addr
        if ip_address != '127.0.0.1':
            abort(401)

        return func(*args, **kwargs)
    return inner
