from pathlib import Path
import configparser
import logging
import os


conf = None

def get():
    return conf

def init():
    global conf
    conf = configparser.ConfigParser()
    conf['DEFAULT']['ROOT_FOLDER'] = str(Path(__file__).parent).replace('\\', '/') + '/'

    try:
        with open('app.cfg', 'r') as config_file:
            logging.info("> Initializing configuration!")
            conf.read_file(config_file)
    except FileNotFoundError:
        logging.info("> Configuration file not found")
        logging.info(">> Creating a new one")
        generate_default()
    except:
        logging.critical("> Unable to open configuration file - don't have enough permissions")

def generate_default():
    global conf
    conf = configparser.ConfigParser()
    # DEFAULT
    conf['DEFAULT']['DEBUG_MODE'] = "True"

    # DOMAIN
    conf['DOMAIN'] = {}
    conf['DOMAIN']['NAME'] = "RemoteLab"
    conf['DOMAIN']['AUTH_METHOD'] = "SHA-256"
    conf['DOMAIN']['TCP_HOST'] = "0.0.0.0"
    conf['DOMAIN']['TCP_PORT'] = "7171"

    # FLASK
    conf['FLASK'] = {}
    conf['FLASK']['SECRET_KEY'] = os.urandom(18).hex()
    conf['FLASK']['LOGGER_NAME'] = "FLASK_LOGGER"

    # DATABASE
    conf['DATABASE'] = {}
    conf['DATABASE']['USER'] = "None"
    conf['DATABASE']['PASSWORD'] = "None"
    conf['DATABASE']['HOST'] = "127.0.0.1"
    conf['DATABASE']['PORT'] = "3306"
    conf['DATABASE']['SCHEMA'] = "Schema"
    conf['DATABASE']['AUTO'] = "True"

    # TCP
    conf['TCP'] = {}
    conf['TCP']['HOST'] = "0.0.0.0"
    conf['TCP']['PORT'] = "7171"
    
    with open('app.cfg', 'w') as configfile:
        conf.write(configfile)
