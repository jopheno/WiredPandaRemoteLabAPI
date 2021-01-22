import socket
import _thread
from threading import Thread
import struct
import logging
import mysql.connector
from modules.tcp_service.client import Client

# MAJOR Version must be changed when incompatible API changes are made
MAJOR_VERSION = 0
# MINOR Version must be changed when new functionalities are added and
# the system remains working even on older versions
MINOR_VERSION = 0


class TcpService:

    def __init__(self, host, port, client_handler):
        try:
            self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            self.running = True
            self.client_handler = client_handler

            self.__host = host
            self.__port = port
            self.__socket.bind((host, port))
        except Exception as ex:
            logging.exception(ex)

    # TODO: TcpService is not being
    # freed correctly because of the
    # running thread from start_listening
    def __del__(self):
        self.running = False
        self.get_socket().close()

    def get_version(self):
        return "v" + str(MAJOR_VERSION) + "." + str(MINOR_VERSION)

    def get_socket(self):
        return self.__socket
    
    def start_listening(self):
        self.__socket.listen()
        logging.info(">> TcpService started successfully at {0}:{1}".format(self.__host, self.__port))
        _thread.start_new_thread(self.run, ())
    
    def run(self):
        while self.running:
            # establish connection with client
            c, addr = self.get_socket().accept()

            endpoint = '{0}:{1}'.format(addr[0], addr[1])

            client = Client(self.client_handler, c, addr)
            self.client_handler.register(endpoint, client)
