import _thread
import threading
import logging
import struct
import time
import config
import serial
from modules.tcp_service.opcodes import op_resolve as tcp_op_resolve
from modules.serial_service.opcodes import op_resolve as serial_op_resolve
from modules.tcp_service import network_message as netmsg


class Client:
    __handler = None

    __id = None
    __token = None
    __lastMessageReceived = None
    __serial_outgoing_messages = []

    def __init__(self, handler, conn, addr):
        self.__handler = handler
        logging.info('Connected to : {0}:{1}'.format(addr[0], addr[1]))
        self.running = True
        self.conn = conn
        self.addr = addr

        self.__id = None
        self.__token = None
        self.__lastMessageReceived = time.time()

        self.rx_thread = _thread.start_new_thread(self.client_listen, ())
        self.tx_thread = _thread.start_new_thread(self.client_speak, ())

    def updateLastRecvMessage(self):
        self.__lastMessageReceived = time.time()
    
    def is_valid(self):
        disconnectAfterSecs = 10
        if time.time() > (self.__lastMessageReceived + disconnectAfterSecs):
            return False
        
        return True

    def set_token(self, token):
        self.__token = token

    def set_id(self, id):
        self.__id = id

    def get_token(self):
        return self.__token

    def get_id(self):
        return self.__id
    
    def send_to_serial(self, msg):
        self.__serial_outgoing_messages.append(msg)

    def handler(self):
        return self.__handler

    def is_running(self):
        return self.running
    
    def send(self, msg):
        try:
            if not self.is_running():
                return None

            # logging.info(">> Client {0} sending opcode {1} (sent: {2})".format(self.__id, msg.get_opcode(), ret))

            if msg != None:
                self.conn.send(msg.get_bytes())
        
        except BrokenPipeError as error:
            # do nothing, client has disconnected just before sending new data
            return False

        return True
    
    def client_speak(self):
        count = 0
        msg_size = 0
        waiting_for_message = False
        waiting_for_message_size = 0
        waiting_since = 0
        ser = serial.Serial('/dev/ttyUSB0', baudrate = 9600, timeout = 1, parity = serial.PARITY_EVEN, stopbits = serial.STOPBITS_TWO)
        #ser = serial.Serial('/dev/ttyUSB0', baudrate = 9600, timeout = 1)
        ser.write_timeout = 0.5
        ser.read_timeout = 1
        
        while self.running:

            # haven't receive a ping message for more than X seconds
            # the client will be disconnected!
            if not self.is_valid():
                self.disconnect()

            # send messages on outgoing queue
            if ser.out_waiting != 0:
                print('Out_waiting: ', ser.out_waiting)
            if self.__serial_outgoing_messages:
                print("Sending a message through serial")
                msg_to_send = self.__serial_outgoing_messages.pop(0)

                try:
                    ser.write(msg_to_send.get_bytes())
                    ser.flush()
                except serial.SerialTimeoutException as ex:
                    print("[EXCEPTION] SerialTimeoutException!!!")

            # listening for serial messages
            if ser.in_waiting >= 4 and waiting_for_message_size == 0:
                size_bytes = ser.read(4)
                msg_size = struct.unpack("!I", bytearray(size_bytes))[0]

                waiting_for_message_size = msg_size
                waiting_since = time.time()

            if waiting_for_message_size != 0 and ser.in_waiting >= waiting_for_message_size:
                opcode_bytes = ser.read(1)
                opcode = struct.unpack("!B", bytearray(opcode_bytes))[0]

                msg_bytes = ser.read(waiting_for_message_size-1)

                serial_op_resolve(self, opcode, msg_bytes)
                waiting_for_message_size = 0
                waiting_since = 0
            
            # if a message is being read for more than 500ms, discard
            if waiting_since != 0 and time.time()-waiting_since > 0.5:
                print("DISCARDING!")
                waiting_for_message_size = 0
                waiting_since = 0

                # close serial comunication and opens it again
                ser.close()
                ser = serial.Serial('/dev/ttyUSB0', baudrate = 9600, timeout = 1, parity = serial.PARITY_EVEN, stopbits = serial.STOPBITS_TWO)
                ser.write_timeout = 0.5
                ser.read_timeout = 1

            if ser.in_waiting == 0:
                # Sleep for 1 milisecond to avoid CPU overusage.
                time.sleep(0.001)

            #msg = netmsg.NetworkOutgoingMessage(3)
            #msg.add_unsigned_long(4)
            #msg.add_unsigned_long(5)
            #msg.add_unsigned_byte(3)
            #msg.add_size()
            
            #self.send(msg)
            count = count + 1
        
        ser.close()

    def client_listen(self):
        conf = config.get()
        while self.is_running():
            try:
                # data received from client
                data = self.conn.recv(1024)
                if not data:
                    break

                size = struct.unpack("!I", bytearray(data[0:4]))[0]
                data = data[4:]

                opcode = data[0]

                if conf["DEFAULT"]["DEBUG_MODE"]:
                    logging.info("> Recv [op_{0}] -> size = {1}".format(size, opcode))

                tcp_op_resolve(self, data[0], data[1:])
            except ConnectionResetError as error:
                # do nothing, client has disconnected when trying to receive more data
                break

        # connection closed
        self.disconnect()
    
    def disconnect(self):
        self.running = False
        with self.handler() as handler:
            handler.log_out(self.get_token())

        self.conn.close()
        logging.info("Bye bye!")
