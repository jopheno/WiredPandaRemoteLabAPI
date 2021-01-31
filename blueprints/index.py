from flask import Blueprint, send_from_directory, current_app, request, escape, abort
from __main__ import get_bs
import logging
import json


bp = Blueprint('home', __name__, static_folder='static')

@bp.route('/api/')
def index():
    server_status = {}
    
    bs = get_bs()
    with bs:
        server_status = bs.get_server_status()
    
    server_status["type"] = "updateInfo"

    return json.dumps(server_status)

@bp.route('/api/logo')
def logo():
    try:
        return current_app.send_static_file('logo.png')
    except FileNotFoundError:
        abort(404)

@bp.route('/api/method', methods=["POST"])
def method():
    token = str(escape(request.values.get('token', '')))
    device_id = int(escape(request.values.get('deviceId', '')))

    method = None
    
    bs = get_bs()
    with bs:
        if bs.auth_user(token) is not None and device_id != 0:
            method = bs.get_device_method(device_id)
        else:
            abort(403)

    try:
        return current_app.send_static_file(method.lower()+'.png')
    except FileNotFoundError:
        abort(404)

@bp.route('/api/auth_device', methods=["POST"])
def auth_device():
    # VirtualHere encrypts the password using MD5
    device_name = str(escape(request.values.get('name', '')))
    device_token_md5 = str(escape(request.values.get('token', '')))

    method = None
    
    bs = get_bs()
    with bs:
        if bs.auth_device(device_name, device_token_md5):
            return "Success"
    
    return "Error"
