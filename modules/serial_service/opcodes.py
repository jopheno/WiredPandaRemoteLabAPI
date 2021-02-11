import struct
import time
import logging
from modules.tcp_service import network_message as netmsg


def parse_output(client, imsg):
    pin_id = imsg.pop_unsigned_int()
    value = imsg.pop_unsigned_byte()

    # Only for debugging purposes (logging contributes increasing latency)
    # print("parse_output", pin_id, value)

    msg = netmsg.NetworkOutgoingMessage(3)
    msg.add_unsigned_int(pin_id)
    msg.add_unsigned_byte(value)
    msg.add_size()

    client.send(msg)

def parse_error(client, imsg):
    a = imsg.pop_unsigned_byte()
    # 10 -> Timeout
    logging.error("parse_error no: " + str(a))

PARSE_OUTPUT = 3
PARSE_ERROR = 4

MAP = {
  3: parse_output,
  4: parse_error
}

def op_resolve(client, opcode, data):

    try:
        if (MAP[opcode] != None):
            imsg = netmsg.NetworkIncomingMessage(opcode, data)
            return MAP[opcode](client, imsg)
    except Exception as ex:
        pass
    
    return None
