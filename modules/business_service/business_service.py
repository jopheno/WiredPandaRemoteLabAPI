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
        server_status["version"] = self.__tcp_service.get_version()
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

    def log_in(self, login, password):
        """
        Responsible for validating user token

        login -> str: set of 32 characters
        password -> str: set of 64 characters
        """
        user_id = None
        secret_key = None

        if self.is_using_ldap() and self.__ldap_service.verify(login, password):
            query = ("SELECT u.id, u.secret FROM `users` u WHERE u.login = '{0}'")

            self.get_db().query(query, login)

            try:
                (user_id, secret_key) = self.get_db().fetch_one()
            except TypeError as err:
                self.get_db().commit()
                self.get_db().close()

            if user_id is None:
                now = datetime.now()
                timestamp = math.floor(datetime.timestamp(now))

                # gets basic info
                info = self.__ldap_service.get_info(login)

                # insert ldap user to database
                self.get_db().query("INSERT INTO `users` (`login`, `password`, `secret`, `last_logged_in`, `email`, `created`) VALUES ('{0}', 'LDAP', NULL, {2}, '{3}', {2});", login, info['password'], timestamp, info['email'])
                self.get_db().commit()
                self.get_db().close()
                
                # gets new user id
                query = ("SELECT u.id, u.secret FROM `users` u WHERE u.login = '{0}'")

                self.get_db().query(query, login)

                try:
                    (user_id, secret_key) = self.get_db().fetch_one()
                except TypeError as err:
                    self.get_db().commit()
                    self.get_db().close()

        else:
            query = ("SELECT u.id, u.secret FROM `users` u WHERE u.login = '{0}' AND u.password = '{1}'")

            self.get_db().query(query, login, password)

            try:
                (user_id, secret_key) = self.get_db().fetch_one()
            except TypeError as err:
                self.get_db().commit()
                self.get_db().close()
                return None

            if user_id is None:
                self.get_db().commit()
                self.get_db().close()
                return None
        
        if secret_key is None:
            secret_key = os.urandom(8).hex()
            self.get_db().query("UPDATE `users` SET `secret`='{0}' WHERE `id`={1};", secret_key, user_id)
        
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
        
        if (device_id is None):
            return False

        self.get_db().query("UPDATE `devices` SET `being_used_by`=NULL, `token`='', `using_since`='0' WHERE `id`={0} AND `being_used_by`={1};", device_id, user_id)
        
        self.get_db().commit()
        self.get_db().close()

        self.get_db().query("SELECT COUNT(*) FROM `devices` WHERE `being_used_by`={0}", user_id)
        
        device_count = None
        try:
            (device_count,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return None

        self.get_db().commit()
        self.get_db().close()
        
        # The user is using another device, token will only be disabled
        # when there is no device left in use by this user.
        if device_count > 0:
            return False

        self.get_db().query("UPDATE `users` SET `secret`=NULL WHERE `id`={0};", user_id)
        
        self.get_db().commit()
        self.get_db().close()

        return True

    def auth_user(self, user_token):
        """
        Responsible for validating user token

        user_token -> str: set of 11 hex characters
        """
        query = ("SELECT u.id FROM `users` u WHERE u.secret = '{0}'")

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

    def stops_using_at(self, device_type_id):
        """
        Get usage time remaining

        device_type_id -> int: identifier of the device type
        """

        conf = config.get()

        self.get_db().query("SELECT MIN(using_since) FROM `devices` d WHERE d.type = {0}", device_type_id)
        
        min_using_since = None
        try:
            (min_using_since,) = self.get_db().fetch_one()
        except TypeError as err:
            self.get_db().commit()
            self.get_db().close()
            return None

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
            return None

        timestamp = min_using_since + allowed_time - int(conf["DEFAULT"]["MINIMUM_WAIT_TIME_IN_SECONDS"])
        now = datetime.now()

        if min_using_since == 0 or min_using_since < datetime.timestamp(now):
            timestamp = datetime.timestamp(now)
        
        timestamp = timestamp + int(conf["DEFAULT"]["MINIMUM_WAIT_TIME_IN_SECONDS"])

        return timestamp

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

    def use(self, user_id, device_type_id, method_id):
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
        
        self.get_db().query("UPDATE `devices` SET `being_used_by`='{0}', `token`='{1}', `method`={2}, `using_since`={3} WHERE `id`={4};", user_id, str(new_token), method_id, timestamp, device_id)
        
        allow_until = timestamp + int(allowed_time) - int(conf["DEFAULT"]["MINIMUM_WAIT_TIME_IN_SECONDS"])
        self.get_db().commit()
        self.get_db().close()
        
        return device_id, new_token, allow_until

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
