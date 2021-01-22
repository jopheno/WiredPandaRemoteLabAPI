from flask import Flask, g
from waitress import serve
import config
from modules import logging as log
from modules.tcp_service.tcp import TcpService
from modules.business_service.business_service import BusinessService
from modules.tcp_service.client_handler import ClientHandler
import logging
import _thread
import signal
import os


app = None
business_service = None

# TODO: Waitress support for production environment
#def init_waitress():

def get_bs():
    global business_service
    conf = config.get()

    if business_service is None:
        db_info = {
            "user": conf["DATABASE"]["USER"],
            "password": conf["DATABASE"]["PASSWORD"],
            "host": conf["DATABASE"]["HOST"],
            "port": int(conf["DATABASE"]["PORT"]),
            "database": conf["DATABASE"]["SCHEMA"],
            "auto-setup": conf["DATABASE"]["AUTO"]
        }

        tcp_info = {
            "host": conf["TCP"]["HOST"],
            "port": int(conf["TCP"]["PORT"]),
        }

        business_service = BusinessService(tcp_info, db_info)

    return business_service

def init_dev():
    log.init()
    config.init()
    conf = config.get()

    my_app = Flask(__name__)
    my_app.secret_key = conf["FLASK"]["SECRET_KEY"]
    my_app.logger = logging.getLogger(conf["FLASK"]["LOGGER_NAME"])

    import routes as routes
    routes.init(my_app)

    return my_app

# TODO: Support for Werkzeug debug mode
if __name__ == "__main__":
    app = init_dev()
    conf = config.get()
    
    get_bs()

    debug = True if conf["DEFAULT"]["DEBUG_MODE"] == "True" else False

    app.run('0.0.0.0', port=8081, debug=False)
