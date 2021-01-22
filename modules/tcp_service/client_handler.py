import threading
import logging
import config


class ClientHandler:
    __clients = None

    def __init__(self):
        self.__clients = {}
        self.__lock = threading.Lock()

    def __enter__(self):
        conf = config.get()

        self.__lock.acquire()

        if conf["DEFAULT"]["DEBUG_MODE"]:
            logging.info("Locking")
        
        return self
  
    def __exit__(self, exc_type, exc_value, traceback):
        conf = config.get()

        if conf["DEFAULT"]["DEBUG_MODE"]:
            logging.info("Unlocking")

        self.__lock.release()

    def register(self, id, client):
        self.__clients[id] = client
