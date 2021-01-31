import struct
import time
import _thread
import logging
import config
from modules.tcp_service import network_message as netmsg


def op_parse_start_session(client, imsg):
    device_type_id = imsg.pop_unsigned_byte()
    method_id = imsg.pop_unsigned_byte()
    token = imsg.pop_string()

    print("op_parse_start_session", device_type_id, method_id, token)

    authenticated = False

    # auto locks and releases threading mutex
    with client.handler() as handler:
        client_id = handler.auth_user(token)
        if client_id is not None:
            client.set_token(token)
            client.set_id(client_id)
            authenticated = True
    
    msg = netmsg.NetworkOutgoingMessage(1)
    msg.add_string(token)

    if not authenticated:
        # device_id zero means error!
        msg.add_unsigned_short(0)

        # unable to authenticate error code
        msg.add_unsigned_byte(0)
        msg.add_string("Unable to authenticate!")
        msg.add_size()

        client.send(msg)
        return None

    device_id = None
    device_token = None
    allow_until = None
    with client.handler() as handler:
        device_id, device_token, allow_until = handler.use(client_id, device_type_id, method_id)
    
    if device_id is None:
        # device_id zero means error!
        msg.add_unsigned_short(0)

        # not enough devices error code
        msg.add_unsigned_byte(1)

        with client.handler() as handler:
            finishes_at = handler.stops_using_at(device_type_id)

        from datetime import datetime
        
        now = datetime.now()
        timestamp = datetime.timestamp(now)
        seconds = finishes_at - timestamp

        # adds one more second (this will ensure that the minimum
        # time of conf["DEFAULT"]["MINIMUM_WAIT_TIME_IN_SECONDS"]
        # will be respected)
        seconds = seconds + 1

        import math

        minutes = math.floor(seconds / 60)

        msg.add_string("Once there isn't an available slot, would you like to enter a queue?\nThe estimated wait time is " + str(minutes) + " minutes.")
        msg.add_size()

        print("There isn't enough devices.", device_type_id, token, device_id)

        client.send(msg)
        return None
    
    client.set_connected(True)
    client.set_device_id(device_id)

    with client.handler() as handler:
        pins = handler.get_device_pins(device_id)

    with client.handler() as handler:
        method = handler.get_device_method(device_id)

    with client.handler() as handler:
        device_name = handler.get_device_name(device_id)

    conf = config.get()
    
    # add device_id
    msg.add_unsigned_short(device_id)

    # method identifier
    # for VirtualHere, it's device's name
    msg.add_string(method)
    msg.add_string(device_name)
    msg.add_string(device_token)
    msg.add_unsigned_int(int(conf["DEFAULT"]["MINIMUM_WAIT_TIME_IN_SECONDS"]))
    msg.add_unsigned_long(allow_until)
    
    # number of pins
    msg.add_unsigned_short(len(pins))

    for pin in pins:
        msg.add_unsigned_int(pin["id"])
        msg.add_string(pin["port"])
        msg.add_unsigned_byte(pin["type"])

    msg.add_size()

    client.send(msg)

    # starts client speak thread
    client.tx_thread = _thread.start_new_thread(client.client_speak, ())

# TODO: a possible implementation is to wait for a
# possible reconnection in the next minute and
# restabilish the connection.

def op_parse_ping(client, imsg):
    timestamp = imsg.pop_unsigned_long()

    # print("op_parse_ping", timestamp)
    client.updateLastRecvMessage()

    msg = netmsg.NetworkOutgoingMessage(2)
    msg.add_unsigned_long(timestamp)
    msg.add_size()

    client.send(msg)

def op_parse_io_info(client, imsg):
    latency = imsg.pop_unsigned_short()
    pin_amount = imsg.pop_unsigned_short()

    info_to_send = []

    for i in range(0, pin_amount):
        pin_id = imsg.pop_unsigned_int()
        pin_type = imsg.pop_unsigned_byte()
        forward = None

        with client.handler() as handler:
            pin_info = handler.get_pin_info(pin_id)

            if pin_info is not None:
                forward = pin_info['forward']
        
        if forward is not None:
            info_to_send.append({'id': pin_id, 'type': pin_type, 'forward': forward})
    
    print("op_parse_io_info", pin_amount, info_to_send)
    
    msg = netmsg.NetworkOutgoingMessage(1)
    msg.add_header()

    msg.add_unsigned_short(int(latency/4))
    msg.add_unsigned_short(len(info_to_send))

    for inf in info_to_send:
        msg.add_unsigned_int(inf['id'])
        msg.add_unsigned_int(inf['forward'])
        msg.add_unsigned_byte(inf['type'])

    msg.add_size_after_header()

    print(msg.get_bytes())

    client.send_to_serial(msg)

def op_parse_update_input(client, imsg):
    pin_id = imsg.pop_unsigned_int()
    pin_value = imsg.pop_unsigned_byte()

    msg = netmsg.NetworkOutgoingMessage(2)
    msg.add_header()

    msg.add_unsigned_int(pin_id)
    msg.add_unsigned_byte(pin_value)

    msg.add_size_after_header()

    client.send_to_serial(msg)

PARSE_START_SESSION = 1
PARSE_PING = 2
PARSE_IO_INFO = 3
PARSE_UPDATE_INPUT = 4

MAP = {
  1: op_parse_start_session,
  2: op_parse_ping,
  3: op_parse_io_info,
  4: op_parse_update_input
}

def op_resolve(client, opcode, data):
    if (MAP[opcode] != None):
        imsg = netmsg.NetworkIncomingMessage(opcode, data)
        return MAP[opcode](client, imsg)
    
    return None
