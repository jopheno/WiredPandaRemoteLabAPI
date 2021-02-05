import struct
import time
import _thread
import logging
import config
from datetime import datetime
from modules.tcp_service import network_message as netmsg


def createQueueUpdateMsg(client, device_type_id, method_id):
    token = client.get_token()
    client_id = client.get_id()

    current_pos = None
    queue_info = None
    with client.handler() as handler:
        current_pos = handler.get_current_pos_on_queue(token, client_id, device_type_id, method_id)
        queue_info = handler.get_queue_info(device_type_id, method_id)

    if current_pos is not None and queue_info is not None:
        # sends queue information
        msg = netmsg.NetworkOutgoingMessage(5)

        # add user token
        msg.add_string(token)

        # number of users
        msg.add_unsigned_byte(len(queue_info["users"]))

        curr_pos = 0
        for user in queue_info["users"]:
            if user["id"] == client_id and user["session"] == token:
                curr_pos = user["pos"]
        
        if curr_pos == 0:
            logging.error("Unable to find user " + str(client_id) + " on queue from device type id " + str(device_type_id))
            return None

        # current position in queue
        msg.add_unsigned_byte(curr_pos)

        # allowed time when in use
        msg.add_unsigned_int(queue_info["allowed_time"])

        # estimated time in seconds
        estimated_time = 0
        with client.handler() as handler:
            estimated_time = handler.get_estimated_time(device_type_id, method_id, curr_pos)

        now = datetime.now()
        timestamp_now = int(datetime.timestamp(now))

        msg.add_unsigned_long(timestamp_now + estimated_time)

        msg.add_size()

        return msg
    else:
        return None

# OPs

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
        device_id, device_token, allow_until = handler.use(token, client_id, device_type_id, method_id)
    
    if device_id is None:
        # device_id zero means error!
        msg.add_unsigned_short(0)

        # not enough devices error code
        msg.add_unsigned_byte(1)

        with client.handler() as handler:
            lastPosition = handler.get_queue_waiting_users_amount(device_type_id, method_id)
            estimated_time_in_seconds = handler.get_estimated_time(device_type_id, method_id, lastPosition+1)

        import math

        minutes = math.floor(estimated_time_in_seconds / 60)

        if minutes <= 0:
            minutes = 1

        msg.add_string("Once there isn't an available slot, would you like to enter a queue?\nThe estimated wait time is " + str(minutes) + " minutes.")
        msg.add_size()

        print("There isn't enough devices.", device_type_id, method_id, token, device_id)

        client.send(msg)
        return None
    
    client.set_connected(True)
    client.set_device_id(device_id)

    with client.handler() as handler:
        pins = handler.get_device_pins(device_id)
        method = handler.get_device_method(device_id)
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

    now = datetime.now()
    timestamp_now = int(datetime.timestamp(now))

    # if I am not in after time, I must evaluate if
    # there is anyone in queue waiting, if so, the
    # current user must enter after time and be noticed
    if not client.is_in_after_time() and timestamp_now % 5 == 0:
        device_id = client.get_device_id()

        if device_id is not None:
            # as I am controling a device, I must verify if there
            # are any other users in the queue waiting
            is_in_after_time = False
            device_type_id = None
            method_id = None
            with client.handler() as handler:
                is_in_after_time = handler.is_in_after_time(device_id)
                device_type_id = handler.get_device_type_id(device_id)
                method_id = handler.get_device_method_id(device_id)

            if is_in_after_time and device_type_id is not None and method_id is not None:

                queue_waiting_users_amount = 0
                with client.handler() as handler:
                    queue_waiting_users_amount = handler.get_queue_waiting_users_amount(device_type_id, method_id)

                if queue_waiting_users_amount > 0:
                    client.set_in_after_time(True)
                    
                    msg = netmsg.NetworkOutgoingMessage(4)
                    msg.add_unsigned_byte(1)
                    msg.add_unsigned_long(timestamp_now)
                    msg.add_size()

                    client.send(msg)
        else:
            # as a waiting user, I must verify if there is any
            # avaliable slot for me to connect to
            pos = None
            with client.handler() as handler:
                pos = handler.get_user_queue_pos(client.get_token(), client.get_id())

            if pos is not None and pos < 1:
                # send connection setup for waiting user's client
                msg = netmsg.NetworkOutgoingMessage(1)
                msg.add_string(client.get_token())

                device_id = None
                device_token = None
                allow_until = None
                
                with client.handler() as handler:
                    device_id, device_token, allow_until = handler.queue_user_use(client.get_token(), client.get_id())
                
                if device_id is None:
                    client.set_connected(False)
                    logging.error("fatal error: position zero from queue is not being able to use device")
                    return
                
                client.set_connected(True)
                client.set_device_id(device_id)

                with client.handler() as handler:
                    pins = handler.get_device_pins(device_id)
                    method = handler.get_device_method(device_id)
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
            elif pos is not None and pos >= 1:
                
                device_type_id = None
                method_id = None
                with client.handler() as handler:
                    device_type_id, method_id = handler.get_user_queue_type(client.get_token(), client.get_id())

                msg = createQueueUpdateMsg(client, device_type_id, method_id)

                if msg is not None:
                    client.send(msg)

    if client.is_in_after_time():
        # if I am in after time, I need to verify if
        # I have not exceeded
        if client.have_after_time_ended():
            msg = netmsg.NetworkOutgoingMessage(4)
            msg.add_unsigned_byte(0)
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
    
    msg = netmsg.NetworkOutgoingMessage(1)
    msg.add_header()

    msg.add_unsigned_short(int(latency/4))
    msg.add_unsigned_short(len(info_to_send))

    for inf in info_to_send:
        msg.add_unsigned_int(inf['id'])
        msg.add_unsigned_int(inf['forward'])
        msg.add_unsigned_byte(inf['type'])

    msg.add_size_after_header()

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

def op_parse_request_to_enter_queue(client, imsg):
    token = imsg.pop_string()
    device_type_id = imsg.pop_unsigned_byte()
    method_id = imsg.pop_unsigned_byte()

    client_id = None
    queue_info = None
    current_pos = None

    client.set_connected(True)

    # auto locks and releases threading mutex
    with client.handler() as handler:
        client_id = handler.auth_user(token)
        if client_id is None:
            client.disconnect()

        current_pos = handler.add_to_queue(token, client_id, device_type_id, method_id)
        logging.info("> Client id {0} entered the queue({1}, {2}) on position {3}".format(client_id, device_type_id, method_id, current_pos))

    msg = createQueueUpdateMsg(client, device_type_id, method_id)

    if msg is not None:
        client.send(msg)


PARSE_START_SESSION = 1
PARSE_PING = 2
PARSE_IO_INFO = 3
PARSE_UPDATE_INPUT = 4
PARSE_REQUEST_TO_ENTER_QUEUE = 5

MAP = {
  1: op_parse_start_session,
  2: op_parse_ping,
  3: op_parse_io_info,
  4: op_parse_update_input,
  5: op_parse_request_to_enter_queue
}

def op_resolve(client, opcode, data):
    if (MAP[opcode] != None):
        imsg = netmsg.NetworkIncomingMessage(opcode, data)
        return MAP[opcode](client, imsg)
    
    return None
