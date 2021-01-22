import mysql.connector
import logging
import config
import os


class DBService():
    __connection = None
    __cursor = None

    def __init__(self, db_info):
        try:
            self.__connection = mysql.connector.connect(user=db_info['user'],
                password=db_info['password'],
                host=db_info['host'],
                database=db_info['database'])
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                logging.error("Something is wrong with your user name or password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                logging.error("Database does not exist")
            else:
                logging.info(err)
        
        logging.info("> Initializing DBService")

        if db_info['auto-setup'] == 'True':
            self.setup_env()
    
    def setup_env(self):
        conf = config.get()

        if "DEV".lower() in conf["DATABASE"]["SCHEMA"].lower():
            self.query("DROP SCHEMA IF EXISTS {0};", conf["DATABASE"]["SCHEMA"])
            self.query("CREATE SCHEMA {0};", conf["DATABASE"]["SCHEMA"])
            self.query("USE {0};", conf["DATABASE"]["SCHEMA"])
            self.commit()

            sorted_list = os.listdir('db/')
            sorted_list.sort()

            for filename in sorted_list:
                self.apply_sql('db/'+filename)

            self.commit()
    
    def get_conn(self):
        self.__connection.ping(reconnect=True, attempts=5, delay=200)
        return self.__connection
    
    def cursor(self):
        self.__cursor = self.get_conn().cursor()
        return self.__cursor

    def query(self, query, *format, **keyword_format):
        conf = config.get()

        if conf["DEFAULT"]["DEBUG_MODE"]:
            logging.info("QUERY: " + query.format(*format, **keyword_format))

        return self.cursor().execute(query.format(*format, **keyword_format))

    def apply_sql(self, filepath):
        conf = config.get()

        with open(filepath) as f:
            if conf["DEFAULT"]["DEBUG_MODE"]:
                logging.info("> Executing {0}".format(filepath))
            try:
                for result in self.cursor().execute(f.read(), multi=True): pass
            except RuntimeError as err:
                pass

        return True
    
    def commit(self):
        self.get_conn().commit()

    def rollback(self):
        self.get_conn().rollback()
    
    def fetch_one(self):
        return self.__cursor.fetchone()
    
    def fetch_all(self):
        return self.__cursor.fetchall()

    def get_row_count(self):
        return self.__cursor.rowcount
    
    def get_last_id(self):
        return self.__cursor.lastrowid
    
    def close(self):
        return self.__cursor.close()
