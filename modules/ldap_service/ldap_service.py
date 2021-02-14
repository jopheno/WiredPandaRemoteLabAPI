import ldap
import logging
import hashlib


class LDAPService():
    def __init__(self, uri, domain, hash_type, user, passwd):
        # removes double quotes from domain
        if domain[0] == '\"' and domain[len(domain)-1] == '\"':
            domain = domain[1:-1]

        self.__options = {
            'uri': uri,
            'domain': domain,
            'hash_type': hash_type,
            'user': user,
            'password': passwd
        }

        # test connection
        self.connect()
        self.verify('teste', 'teste')
        self.disconnect()
    
    def __del__(self):
        self.disconnect()
    
    def get_options(self):
        return self.__options
    
    def connect(self):
        options = self.get_options()

        self.__conn = ldap.initialize(options['uri'])
        self.__conn.set_option(ldap.OPT_REFERRALS, 0)
        self.__conn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
        self.__conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 5)

        # bind if needed
        if options['user'] != 'None' and options['password'] != 'None':
            login = 'cn=' + options['user'] + ',' + options['domain']
            self.__conn.simple_bind_s(login, hashlib.md5(options['password'].encode()).digest().hex())

    def disconnect(self):
        self.__conn = None
    
    def verify(self, user, passwd):
        self.connect()
        options = self.get_options()
        result = None
        try:
            result, = self.__conn.search_s(options['domain'], ldap.SCOPE_SUBTREE, 'uid=' + user, ['cn', 'uid', 'mail', 'userpassword'])
        except ValueError as err:
            self.disconnect()
            return False

        self.disconnect()

        hash_passwd = passwd

        if options['hash_type'] == 'MD5':
            hash_passwd = hashlib.md5(passwd.encode()).digest().hex()
        
        if options['hash_type'] == 'SHA256':
            hash_passwd = hashlib.sha256(passwd.encode()).digest().hex()

        try:
            if result[1]['uid'][0].decode() == user and result[1]['userPassword'][1][5:].decode() == hash_passwd:
                return True
        except IndexError as err:
            pass
        except KeyError as err:
            pass
        
        return False

    def get_info(self, user):
        self.connect()
        options = self.get_options()
        result, = self.__conn.search_s(options['domain'], ldap.SCOPE_SUBTREE, 'uid=' + user, ['mail', 'userpassword'])
        self.disconnect()

        ret = {
            'email': None,
            'password': None
        }

        try:
            ret['email'] = result[1]['mail'][0].decode()
        except KeyError:
            ret['email'] = 'not_found@unifesp.br'

        try:
            ret['password'] = result[1]['userPassword'][1][5:].decode()
        except KeyError:
            ret['password'] = 'not_found'

        return ret
