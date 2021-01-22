import logging


def init():
    logging.basicConfig(format="[%(asctime)s] %(message)s", datefmt="%d/%m/%Y %I:%M:%S", level=logging.DEBUG)
