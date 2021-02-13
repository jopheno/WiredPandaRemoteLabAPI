from blueprints import __all__
import logging
import importlib


def init(app):
    logging.info("> Initializing routes!")
    for blueprint in __all__:
        imp = importlib.import_module("blueprints."+blueprint)
        logging.info(">> BP '" + blueprint + "' imported successfully")
        prefix = None

        try:
            prefix = imp.bp_prefix
        except AttributeError:
            pass

        if prefix is not None:
            app.register_blueprint(imp.bp, url_prefix=prefix)
        else:
            app.register_blueprint(imp.bp)
