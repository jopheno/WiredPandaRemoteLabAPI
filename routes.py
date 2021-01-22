from blueprints import __all__
import logging
import importlib


def init(app):
    logging.info("> Initializing routes!")
    for blueprint in __all__:
        imp = importlib.import_module("blueprints."+blueprint)
        logging.info(">> "+blueprint+"_bp imported successfully")
        app.register_blueprint(imp.bp)
