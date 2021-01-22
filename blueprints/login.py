from flask import Blueprint, request, escape, g, current_app
from __main__ import get_bs
import logging
import config
import json

bp = Blueprint('login', __name__)


@bp.route('/login', methods=["GET"])
def login_get():
    return "Hey!"

@bp.route('/api/login', methods=["POST"])
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

@bp.route('/test')
def test():
    # with current_app.app_context():
    bs = get_bs()
    query = ("SELECT '{0}'")

    with bs:
        bs.get_db().query(query, "hello")
        for (first_name,) in bs.get_db().fetch_all():
            return first_name
        
    return "Nothing"