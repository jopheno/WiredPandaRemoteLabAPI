import mysql.connector
from modules.db_service.db_service import DBService
from modules.ldap_service.ldap_service import LDAPService
from modules.tcp_service.tcp import TcpService
from modules.tcp_service.client_handler import ClientHandler
from datetime import datetime
import hashlib
import logging
import secrets
import config
import time
import math
import os


# MAJOR Version must be changed when incompatible API changes are made
MAJOR_VERSION = 0
# MINOR Version must be changed when new functionalities are added and
# the system remains working even on older versions
MINOR_VERSION = 0

class BusinessService(ClientHandler):
    __tcp_service = None
    __db_service = None
    __started_at = None

    def __init__(self, tcp_info, db_info):
        super().__init__()

        self.__started_at = time.time()
        self.__db_service = DBService(db_info)
        self.__ldap_service = None

        conf = config.get()

        if conf['LDAP']['ENABLE'] == 'True':
            self.__ldap_service = LDAPService(conf['LDAP']['URI'], conf['LDAP']['DOMAIN'], conf['LDAP']['HASH_TYPE'], conf['LDAP']['USER'], conf['LDAP']['PASSWORD'])

        self.remove_hangling_connections()

        if tcp_info is not None:
            self.__tcp_service = TcpService(tcp_info['host'], tcp_info['port'], self)
            self.__tcp_service.start_listening()
    
    def __del__(self):
        if self.__tcp_service is not None:
            del self.__tcp_service

        del self.__db_service

    def get_version_str(self):
        return "v" + str(MAJOR_VERSION) + "." + str(MINOR_VERSION)

    def get_version(self):
        return MAJOR_VERSION, MINOR_VERSION

    def is_using_ldap(self):
        return self.__ldap_service != None
    
    def get_db(self):
        return self.__db_service
    
    def register(self, id, client):
        super().register(id, client)
    
    # business methods

    def remove_hangling_connections(self):
        """
        This will remove any on-going sessions that are still available in the database
        """

        logging.info("> Cleaning old-sessions!")

        self.get_db().query("UPDATE `devices` SET `being_used_by`=NULL, `token`='', `using_since`='0';")
        self.get_db().query("TRUNCATE `user_sessions`;")
        self.get_db().query("TRUNCATE `device_type_queue`;")
        
        self.get_db().commit()
        self.get_db().close()

    def get_uptime(self):
        """
        Retrieve server's uptime information
        """

        from math import floor

        delta_time = time.time() - self.__started_at

        days = floor(delta_time/(24*3600))
        delta_time = delta_time - (days*24*3600)

        hours = floor(delta_time/(3600))
        delta_time = delta_time - (hours*3600)

        minutes = floor(delta_time/(60))
        delta_time = delta_time - (minutes*60)

        seconds = floor(delta_time)

        ret = {
            "days": days,
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds
        }

        return ret

    def get_server_status(self):
        """
        Retrieve server status information

        returns {
            "uptime": "10d 5hrs 21min 10s",
            "domainName": "DOMAIN_NAME",
            "status": "Online",
            "version": "v1.0.0",
            "devicesAmount": {
                "DEVICE_NAME": DEVICE_AMOUNT,
            },
            "devicesAvailable": {
                "DEVICE_NAME": DEVICE_AMOUNT,
            },
            "methods": {
                "METHOD_ID": METHOD_NAME,
            }
        }
        """

        conf = config.get()

        server_status = {}

        uptime = self.get_uptime()

        server_status["status"] = "Online"
        server_status["version"] = self.get_version_str()
        server_status["domainName"] = conf["DOMAIN"]["NAME"]
        server_status["uptime"] = "{0}d {1}hrs {2}min {3}s".format(uptime["days"], uptime["hours"], uptime["minutes"], uptime["seconds"])
        server_status["devices"] = self.get_devices()
        server_status["devicesAvailable"] = self.get_device_slots()
        server_status["devicesAmount"] = self.get_all_device_slots()
        server_status["methods"] = self.get_all_methods()
        
        return server_status
    
    def get_devices(self):
        """
        Get all devices
        """

        devices = {}

        query = ("SELECT t.id, t.name FROM `device_types` t;")

        self.get_db().query(query)

        for (device_type_id, device_type_name) in self.get_db().fetch_all():
            devices[device_type_name] = device_type_id
        
        self.get_db().commit()
        self.get_db().close()

        return devices
    
    def get_all_methods(self):
        """
        Get all methods
        """

        methods = {}

        query = ("SELECT t.id, t.name FROM `device_type_methods` t;")

        self.get_db().query(query)

        for (method_id, method_name) in self.get_db().fetch_all():
            methods[method_name] = method_id
        
        self.get_db().commit()
        self.get_db().close()

        return methods
    
    def get_all_devices(self):
        """
        Get amount of devices
        """
        devices = {}

        query = ("\
            SELECT device_type.name, COUNT(devices.id) \
            FROM `device_types` device_type \
                LEFT JOIN `devices` devices \
                ON device_type.id = devices.`type`;\
        ")

        self.get_db().query(query)

        for (device_name, amount) in self.get_db().fetch_all():
            devices[device_name] = amount
        
        self.get_db().commit()
        self.get_db().close()

        return devices
    
    def get_device_slots(self):
        """
        Get amount of devices available for use
        """
        devices = {}

        query = ("\
            SELECT device_type.name, COUNT(devices.id) \
            FROM `device_types` device_type \
                LEFT JOIN \
                    (SELECT * FROM `devices` \
                        WHERE being_used_by IS NULL) devices \
                ON device_type.id = devices.`type`;\
        ")

        self.get_db().query(query)

        for (device_name, amount) in self.get_db().fetch_all():
            devices[device_name] = amount
        
        self.get_db().commit()
        self.get_db().close()
        
        return devices
    
    def get_all_device_slots(self):
        """
        Get total amount of devices
        """
        devices = {}

        query = ("\
            SELECT device_type.name, COUNT(devices.id) \
            FROM `device_types` device_type \
                LEFT JOIN \
                    (SELECT * FROM `devices` ) devices \
                ON device_type.id = devices.`type`;\
        ")

        self.get_db().query(query)

        for (device_name, amount) in self.get_db().fetch_all():
            devices[device_name] = amount
        
        self.get_db().commit()
        self.get_db().close()
        
        return devices
    
    def create_new_session(self, user_id):

        secret_key = os.urandom(8).hex()
        
        self.get_db().query("INSERT INTO `user_sessions` (`user_id`, `secret`) VALUES ({0}, '{1}');", user_id, secret_key)
        self.get_db().commit()
        self.get_db().close()

        return secret_key

    def log_in(self, login, password):
        """
        Responsible for validating user token

        login -> str: set of 32 characters
        password -> str: set of 64 characters
        """

        user_id = None

        if self.is_using_ldap() and self.__ldap_service.verify(login, password):
            query = ("SELECT u.id FROM `users` u WHERE u.login = '{0}'")

            self.get_db().query(query, login)

            try:
                (user_id,) = self.get_db().fetch_one()
            except TypeError as err:
                self.get_db().commit()
                self.get_db().close()

            if user_id is None:
                now = datetime.now()
                timestamp = math.floor(datetime.timestamp(now))

                # gets basic info
                info = self.__ldap_service.get_info(login)

                # insert ldap user to database
                self.get_db().query("INSERT INTO `users` (`login`, `password`, `last_logged_in`, `email`, `created`) VALUES ('{0}', 'LDAP', {1}, '{2}', {1});", login, timestamp, info['email'])
                self.get_db().commit()
                self.get_db().close()
                
                # gets new user id
                query = ("SELECT u.id FROM `users` u WHERE u.login = '{0}'")

                self.get_db().query(query, login)

                try:
                    (user_id, ) = self.get_db().fetch_one()
                except TypeError as err:
                    self.get_db().commit()
                    self.get_db().close()

        else:
            query = ("SELECT u.id FROM `users` u WHERE u.login = '{0}' AND u.password = '{1}'")

            self.get_db().query(query, login, password)

            try:
                (user_id,) = self.get_db().fetch_one()
            except TypeError as err:
                self.get_db().commit()
                self.get_db().close()
                return None

            if user_id is None:
                self.get_db().commit()
                self.get_db().close()
                return None
        
        secret_key = self.create_new_session(user_id)
        
        self.get_db().commit()
        self.get_db().close()

        return secret_key
    
    def log_out(self, user_token, device_id):
        """
        Responsible for validating user token

        user_token -> str: set of 11 hex characters
        """

        user_id = self.auth_user(user_token)

        if (user_id is None):
            return False
        
        # deletes current session
        self.get_db().query("DELETE FROM `user_sessions` WHERE `user_id`={0} AND `secret`='{1}';", user_id, user_token)
        
        self.get_db().commit()
        self.get_db().close()

        # removes user from queue
        self.remove_from_queue(user_token, user_id)
        
        if (device_id is not None):
            device_type_id = self.get_device_type_id(device_id)
            method_id = self.get_device_method_id(device_id)

            self.get_db().query("UPDATE `devices` SET `being_used_by`=NULL, `session`=NULL, `token`='', `using_since`='0' WHERE `id`={0} AND `being_used_by`={1} AND `session`='{2}';", device_id, user_id, user_token)
            self.get_db().query("UPDATE `device_type_queue` q SET q.position=(q.position - 1) WHERE q.type={0} AND q.method_id={1};", device_type_id, method_id)

            self.get_db().commit()
            self.get_db().close()

        return True

    def auth_user(self, user_token):
        """
        Responsible for validating user token

        user_token -> str: set of 11 hex characters
        """

        query = ("SELECT s.user_id FROM `user_sessions` s WHERE s.secret = '{0}'")

        self.get_db().query(query, user_token)

        user_id = None

        try:
            (user_id,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return None

        self.get_db().commit()
        self.get_db().close()

        return user_id
    
    def get_device_type_methods(self, device_type_id):
        """
        Get device method type

        device_type_id -> int: identifier of the device type
        """

        results = []
        query = ("SELECT m.name, m.latency FROM `device_type_methods` m INNER JOIN (SELECT * FROM `device_types` WHERE `id` = {0}) t ON m.type = t.id")

        self.get_db().query(query, device_type_id)

        try:
            for (name, latency) in self.get_db().fetch_all():
                results.append({
                    "name": name,
                    "latency": latency
                })
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return []
        
        self.get_db().commit()
        self.get_db().close()

        return results
    
    def get_device_method(self, device_id):
        """
        Get device name

        device_id -> int: identifier of the device
        """

        self.get_db().query("SELECT m.name FROM `device_type_methods` m INNER JOIN (SELECT * FROM `devices` WHERE `id` = {0}) t ON t.method = m.id", device_id)
        
        device_method = None
        try:
            (device_method,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return None
        
        return device_method
    
    def get_device_serial_port(self, device_id):
        """
        Get device name

        device_id -> int: identifier of the device

        returns serial_port -> str: set of 22 characters
        """

        self.get_db().query("SELECT serial_port from `devices` d WHERE d.id = {0}", device_id)
        
        serial_port = None
        try:
            (serial_port,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return None
        
        return serial_port
    
    def get_device_name(self, device_id):
        """
        Get device name

        device_id -> int: identifier of the device
        """

        self.get_db().query("SELECT CONCAT(NAME, ' [', d.id, ']') AS DEVICE_NAME FROM (SELECT id, type FROM `devices` WHERE id = {0}) d INNER JOIN `device_types` t ON t.id = d.type", device_id)
        
        device_name = None
        try:
            (device_name,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return None
        
        return device_name
    
    def get_device_type_id_by_name(self, device_name):
        """
        Get device id by name

        device_name -> str: device type name
        """

        self.get_db().query("SELECT id FROM `device_types` WHERE NAME LIKE '{0}'", device_name)
        
        device_type_id = None
        try:
            (device_type_id,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return None
        
        return device_type_id
    
    def get_allowed_time_from_device_type(self, device_type_id):

        self.get_db().query(
            "SELECT d.allowed_time FROM `device_types` d WHERE d.id = '{0}'",
            device_type_id
        )

        allowed_time = None
        try:
            (allowed_time,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return 0

        return allowed_time

    def stops_using_at(self, device_type_id, method_id):
        """
        Get time remaining

        device_type_id -> int: identifier of the device type
        method_id -> int: identifier of the method used
        """

        conf = config.get()

        self.get_db().query("SELECT MIN(using_since) FROM `devices` d WHERE d.type = {0} AND d.method = {1}", device_type_id, method_id)
        
        min_using_since = None
        try:
            (min_using_since,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return None
        
        if min_using_since is None:
            min_using_since = 0

        allowed_time = self.get_allowed_time_from_device_type(device_type_id)

        timestamp = min_using_since + allowed_time - int(conf["DEFAULT"]["MINIMUM_WAIT_TIME_IN_SECONDS"])
        now = datetime.now()

        if min_using_since == 0 or timestamp < datetime.timestamp(now):
            timestamp = datetime.timestamp(now)
        
        timestamp = timestamp + int(conf["DEFAULT"]["MINIMUM_WAIT_TIME_IN_SECONDS"])

        return timestamp
    
    def get_queue_waiting_users_amount(self, device_type_id, method_id):
        """
        Get amount of users currently waiting in queue

        device_type_id -> int: identifier of the device type
        method_id -> int: identifier of the method
        """
        self.get_db().query("SELECT count(*) FROM `device_type_queue` t WHERE t.`type` = {0} AND t.`method_id` = {1}", device_type_id, method_id)
        
        count = None
        try:
            (count,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return 0
        
        return count

    def get_queue_waiting_users(self, device_type_id, method_id):
        """
        Retrieves all waiting users in queue and their position

        device_type_id -> int: identifier of the device type
        method_id -> int: identifier of the method
        """
        users = []
        query = ("SELECT q.user_id, q.session, q.position FROM `device_type_queue` q WHERE q.type = {0} AND q.method_id = {1}")

        self.get_db().query(query, device_type_id, method_id)

        try:
            for (user_id, session, position) in self.get_db().fetch_all():
                users.append({
                    "id": user_id,
                    "session": session,
                    "pos": position,
                })
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return []
        
        self.get_db().commit()
        self.get_db().close()

        return users
    
    def get_user_queue_pos(self, user_token, user_id):
        """
        Retrieves current position on queue if applicable

        user_token -> str: set of 11 hex characters
        user_id -> int: identifier of user
        """

        self.get_db().query("SELECT t.position FROM `device_type_queue` t WHERE t.`user_id` = {0} AND t.`session` = '{1}'", user_id, user_token)
        
        position = None
        try:
            (position,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return None
        
        return position
    
    def get_user_queue_type(self, user_token, user_id):
        """
        Retrieves device_type_id of user's queue, if applicable

        user_token -> str: set of 11 hex characters
        user_id -> int: identifier of user

        returns device_type_id, method_id
        """

        self.get_db().query("SELECT t.type, t.method_id FROM `device_type_queue` t WHERE t.`user_id` = {0} AND t.`session` = '{1}'", user_id, user_token)
        
        device_type_id = None
        method_id = None
        try:
            (device_type_id, method_id) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return None, None
        
        return device_type_id, method_id
    
    def queue_user_use(self, user_token, user_id):
        """
        Retrieves current position on queue if applicable

        user_token -> str: set of 11 hex characters
        user_id -> int: identifier of user
        """

        pos = self.get_user_queue_pos(user_token, user_id)

        if pos is not None and pos < 1:
            device_type_id, method_id = self.get_user_queue_type(user_token, user_id)

            self.get_db().query("DELETE FROM `device_type_queue` WHERE `user_id`={0} AND `session`='{1}';", user_id, user_token)
            self.get_db().commit()
            self.get_db().close()

            device_id, new_token, allow_until = self.use(user_token, user_id, device_type_id, method_id)

            return device_id, new_token, allow_until

        return None, None, None

    def get_queue_info(self, device_type_id, method_id):
        """
        Retrieves a specific device type queue information

        device_type_id -> int: identifier of the device type
        """

        ret = {
            "estimated_time": None,
            "allowed_time": None,
            "users": []
        }

        ret["users"] = self.get_queue_waiting_users(device_type_id, method_id)
        ret["estimated_time"] = self.get_estimated_time(device_type_id, method_id, len(ret["users"]))
        ret["allowed_time"] = self.get_allowed_time_from_device_type(device_type_id)

        return ret

    def get_estimated_time(self, device_type_id, method_id, current_pos):
        # evaluates current user time remaining
        finishes_at = self.stops_using_at(device_type_id, method_id)
        
        now = datetime.now()
        timestamp = datetime.timestamp(now)
        seconds_for_actual_user_to_finish = finishes_at - timestamp

        # add "device type allowed time" for each other user in queue

        allowed_time = self.get_allowed_time_from_device_type(device_type_id)

        # being in the first position of the line means you are next,
        # so current_pos must be zero for other_users_estimated_seconds
        # to be zero
        current_pos = current_pos - 1

        if current_pos < 0:
            current_pos = 0

        other_users_estimated_seconds = current_pos * (allowed_time + 10)

        # estimated time in seconds is the sum of current session
        # estimated finish time and other users

        estimated_time_in_seconds = seconds_for_actual_user_to_finish + other_users_estimated_seconds

        # on every estimation increase 10 seconds as the time
        # needed for disconnecting a user and connecting another

        estimated_time_in_seconds = estimated_time_in_seconds + 10
        
        return int(estimated_time_in_seconds)
    
    def get_current_pos_on_queue(self, user_token, user_id, device_type_id, method_id):
        """
        Retrieves the user's current pos on a determinated queue

        user_token -> str: set of 11 hex characters
        user_id -> int: identifier of user
        device_type_id -> int: identifier of the device type
        method_id -> int: identifier of the method
        """

        self.get_db().query(
            "SELECT q.position FROM `device_type_queue` q WHERE q.user_id = {0} AND q.session = '{1}' AND q.type = {2} AND q.method_id = {3}",
            user_id, user_token, device_type_id, method_id
        )

        current_pos = None
        try:
            current_pos, = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            pass

        return current_pos
    
    def add_to_queue(self, user_token, user_id, device_type_id, method_id):
        """
        Adds user to queue

        user_token -> str: set of 11 hex characters
        user_id -> int: identifier of user
        device_type_id -> int: identifier of the device type
        method_id -> int: identifier of the method
        """

        self.get_db().query(
            "SELECT q.user_id, q.session FROM `device_type_queue` q WHERE q.user_id = '{0}' AND q.session = '{1}'",
            user_id, user_token
        )

        found_user_id = None
        found_session = None
        try:
            (found_user_id, found_session) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            pass

        if found_user_id == user_id and found_session == user_token:
            logging.error("same user, in the same session, is trying to enter a queue but it is already registered to another")
            return None

        total_amount = self.get_queue_waiting_users_amount(device_type_id, method_id)

        # insert new user to queue
        self.get_db().query("INSERT INTO `device_type_queue` (`type`, `method_id`, `user_id`, `session`, `position`) VALUES ({0}, {1}, {2}, '{3}', {4});",
            device_type_id, method_id, user_id, user_token, total_amount + 1)
        self.get_db().commit()
        self.get_db().close()

        return total_amount + 1
    
    def remove_from_queue(self, user_token, user_id):
        """
        Adds user to queue

        user_token -> str: set of 11 hex characters
        user_id -> int: identifier of user
        """

        self.get_db().query(
            "SELECT q.id, q.type, q.method_id, q.position FROM `device_type_queue` q WHERE q.user_id = '{0}' AND q.session = '{1}'",
            user_id, user_token
        )

        queue_pos_id = None
        device_type_id = None
        method_id = None
        pos = None
        try:
            (queue_pos_id, device_type_id, method_id, pos,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return False
        
        if queue_pos_id is None or device_type_id is None or pos is None:
            return False

        self.get_db().query("UPDATE `device_type_queue` q SET q.position=(q.position - 1) WHERE q.type={0} AND q.method_id={1} AND q.position > {2};", device_type_id, method_id, pos)
        self.get_db().query("DELETE FROM `device_type_queue` WHERE `id`={0};", queue_pos_id)

        self.get_db().commit()
        self.get_db().close()

        return True

    def auth_device(self, device_name, device_token_md5):
        """
        Verify if device token matches

        device_name -> str: device name
        device_token -> str: this is a generated token, and it is expected to be MD5 hashed
        """

        parts = device_name.split(' ')
        length = len(parts)

        device_type = parts[0:(length-1)][0]

        for i in range(1, length-1):
            device_type = device_type + " " + parts[0:(length-1)][i]

        device_id = parts[(length-1):length][0]
        device_id = device_id[1:(len(device_id)-1)]

        if device_id is None:
            return False

        self.get_db().query("SELECT token FROM `devices` t WHERE t.`id` = {0}", device_id)
        
        device_token = None
        try:
            (device_token,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return False

        result = hashlib.md5(device_token.encode()).digest().hex()

        print(str(result), device_token_md5, device_id)

        if (result == device_token_md5):
            return True
        
        return False

    def use(self, user_token, user_id, device_type_id, method_id):
        """
        Apply for using a device

        device_type_id -> int: identifier of the device type
        """

        conf = config.get()

        self.get_db().query(
            "SELECT d.id FROM `devices` d WHERE d.type = '{0}' AND d.being_used_by is NULL",
            device_type_id
        )

        device_id = None
        try:
            (device_id,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return None, None, None

        self.get_db().query(
            "SELECT d.allowed_time FROM `device_types` d WHERE d.id = '{0}'",
            device_type_id
        )

        allowed_time = None
        try:
            (allowed_time,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return None, None, None
        
        new_token = secrets.token_hex(6)

        now = datetime.now()
        timestamp = math.floor(datetime.timestamp(now))
        
        self.get_db().query("UPDATE `devices` SET `being_used_by`='{0}', `session`='{1}', `token`='{2}', `method`={3}, `using_since`={4} WHERE `id`={5};", user_id, user_token, str(new_token), method_id, timestamp, device_id)
        
        allow_until = timestamp + int(allowed_time) - int(conf["DEFAULT"]["MINIMUM_WAIT_TIME_IN_SECONDS"])
        self.get_db().commit()
        self.get_db().close()
        
        return device_id, new_token, allow_until
    
    def get_device_type_id(self, device_id):
        """
        Gets device type based on device identification

        device_id -> int: identifier of the device
        """

        query = ("SELECT d.type FROM `devices` d WHERE d.id = {0}")
        self.get_db().query(query, device_id)

        device_type_id = None
        try:
            (device_type_id,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return None
        
        return device_type_id
    
    def get_device_method_id(self, device_id):
        """
        Gets device method id based on device identification

        device_id -> int: identifier of the device
        """

        query = ("SELECT d.method FROM `devices` d WHERE d.id = {0}")
        self.get_db().query(query, device_id)

        method_id = None
        try:
            (method_id,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return None
        
        return method_id
    
    def get_device_using_time(self, device_id):
        """
        Retrieves the amount of seconds that the device is being used

        device_id -> int: identifier of the device
        """

        now = datetime.now()
        timestamp = datetime.timestamp(now)

        self.get_db().query(
            "SELECT d.using_since FROM `devices` d WHERE d.id = '{0}'",
            device_id
        )

        using_since = None
        try:
            (using_since,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return None

        seconds = timestamp - using_since
        
        if seconds < 0:
            seconds = 0
        
        return seconds
    
    def is_in_after_time(self, device_id):
        """
        Checks whether device user is already in after time

        device_id -> int: identifier of the device
        """

        conf = config.get()

        seconds = self.get_device_using_time(device_id)
        device_type_id = self.get_device_type_id(device_id)
        allowed_time = self.get_allowed_time_from_device_type(device_type_id)
        seconds_in_time = allowed_time - int(conf["DEFAULT"]["MINIMUM_WAIT_TIME_IN_SECONDS"])

        if seconds > seconds_in_time:
            return True
        
        return False
    
    def has_time_left(self, device_id):
        """
        Checks whether device user has some time left (whether in after time or not)

        device_id -> int: identifier of the device
        """

        conf = config.get()

        seconds = self.get_device_using_time(device_id)
        device_type_id = self.get_device_type_id(device_id)
        allowed_time = self.get_allowed_time_from_device_type(device_type_id)

        # allowed time is regular time plus after time

        if seconds > allowed_time:
            return False
        
        return True

    def get_device_pins(self, device_id):
        """
        Retrieves all available pins for specific device

        device_id -> int: identifier of the device
        """
        results = []
        query = ("SELECT p.id, p.port, p.type, p.forward_from FROM `device_pins` p WHERE p.device = {0}")

        self.get_db().query(query, device_id)

        try:
            for (id, port, type, forward_from) in self.get_db().fetch_all():
                results.append({
                    "id": id,
                    "port": port,
                    "type": type,
                    "forward_from": forward_from
                })
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return []
        
        self.get_db().commit()
        self.get_db().close()

        return results

    def get_pin_info(self, pin_id):
        """
        Retrieves all available pins for specific device

        pin_id -> int: pin identifier
        """

        query = ("SELECT p.port, p.type, p.forward_from FROM `device_pins` p WHERE p.id = {0}")

        self.get_db().query(query, pin_id)

        try:
            (pin_port, pin_type, pin_forward_from) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return None
        
        self.get_db().commit()
        self.get_db().close()

        result = {
            'port': pin_port,
            'type': pin_type,
            'forward': pin_forward_from
        }

        return result
