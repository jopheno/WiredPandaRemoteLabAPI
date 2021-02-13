from flask import send_from_directory, current_app, request, escape, abort
from __main__ import get_bs
import logging
import json
import config
from blueprints.api.bp import bp, bp_prefix


@bp.route('/')
def index():
    server_status = {}
    
    bs = get_bs()
    with bs:
        server_status = bs.get_server_status()
    
    server_status["type"] = "updateInfo"

    return json.dumps(server_status)

@bp.route('/logo')
def logo():
    try:
        return current_app.send_static_file('logo.png')
    except FileNotFoundError:
        abort(404)

@bp.route('/method', methods=["POST"])
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

@bp.route('/auth_device', methods=["POST"])
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

@bp.route('/login', methods=["POST"])
def login_post():
    login = str(escape(request.values.get('login', '')))
    passwd = str(escape(request.values.get('passwd', '')))

    conf = config.get()
    
    logging.info("Trying to log in with ({0}, {1})".format(login, passwd))

    secret_key = None

    bs = get_bs()
    with bs:
        secret_key = bs.log_in(login, passwd)
    
    if secret_key is None:
        return json.dumps({"reply": "error", "msg": "Username and password mismatch!"})
    
    resp = {
        "reply": "ok",
        "token": secret_key,
        "host": conf["DOMAIN"]["TCP_HOST"],
        "port": int(conf["DOMAIN"]["TCP_PORT"])
    }

    return json.dumps(resp)
