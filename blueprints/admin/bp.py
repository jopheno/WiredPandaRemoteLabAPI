from flask import Blueprint, request, abort, redirect, url_for, session
from functools import wraps
from __main__ import get_bs

bp = Blueprint('admin', __name__, static_folder='static', template_folder='templates')
bp_prefix = '/admin'


def localhost(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip_address = request.remote_addr
        if ip_address != '127.0.0.1':
            abort(401)

        return f(*args, **kwargs)

    return decorated_function

def must_be_logged_in(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if 'user_token' not in session:
            return redirect(url_for('admin.login'))

        user_id = None

        bs = get_bs()
        with bs:
            user_id = bs.auth_user(session['user_token'])

        if user_id is None:
            session.pop('user_token')
            return redirect(url_for('admin.login'))

        return f(*args, **kwargs)

    return decorated_function

#@restricted(access_level=1)
def restricted(access_level):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            print(access_level)
            return func(*args, **kwargs)
        return wrapper
    return decorator
