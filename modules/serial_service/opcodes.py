import struct
import time
from modules.tcp_service import network_message as netmsg


def parse_output(client, imsg):
    pin_id = imsg.pop_unsigned_int()
    value = imsg.pop_unsigned_byte()

    print("parse_output", pin_id, value)

    msg = netmsg.NetworkOutgoingMessage(3)
    msg.add_unsigned_int(pin_id)
    msg.add_unsigned_byte(value)
    msg.add_size()

    client.send(msg)

PARSE_OUTPUT = 3

MAP = {
  3: parse_output
}

def op_resolve(client, opcode, data):

    try:
        if (MAP[opcode] != None):
            imsg = netmsg.NetworkIncomingMessage(opcode, data)
            return MAP[opcode](client, imsg)
    except Exception as ex:
        pass
    
    return None
