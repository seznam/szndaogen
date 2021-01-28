import typing
from functools import wraps
from time import sleep

from mysql.connector import Error
from mysql.connector import MySQLConnection
from mysql.connector.pooling import MySQLConnectionPool
from mysql.connector.pooling import errors
from ..tools.log import Logger
from ..config import Config


class DBI:
    is_initialized = False
    connection_config: dict = None
    connection_pool: MySQLConnectionPool = None

    def __init__(self):
        self._is_in_transaction = False
        self._is_in_pass_dbi = False
        self._is_in_self_dbi = False
        self._connection = None
        DBI._init()

    @classmethod
    def _init(cls):
        if cls.is_initialized:
            return
        cls.connection_config = {
            "host": Config.MYSQL_HOST,
            "port": Config.MYSQL_PORT,
            "database": Config.MYSQL_DATABASE,
            "user": Config.MYSQL_USER,
            "password": Config.MYSQL_PASSWORD,
        }
        cls.connection_pool = (
            MySQLConnectionPool(
                pool_name="app_pool",
                pool_size=Config.MYSQL_POOL_SIZE,
                pool_reset_session=False,
                **cls.connection_config
            )
            if Config.MYSQL_POOL_SIZE
            else None
        )

    def _get_connection(self):
        if not self._connection:
            if DBI.connection_pool:
                try_get_pool_conn_counter = Config.MYSQL_POOL_CONNECTION_TIMEOUT
                while not self._connection:
                    try:
                        if not try_get_pool_conn_counter:
                            raise Exception(
                                "Pool connection timeout error. No connection avaliable in pool during {}ms".format(
                                    Config.MYSQL_POOL_CONNECTION_TIMEOUT
                                )
                            )
                        self._connection = DBI.connection_pool.get_connection()
                    except errors.PoolError:
                        Logger.log.debug(
                            "DBI._get_connection.wait_for_pool_connection: {}".format(try_get_pool_conn_counter)
                        )
                        try_get_pool_conn_counter -= 1
                        sleep(0.001)
            else:
                self._connection = MySQLConnection(**DBI.connection_config)
            Logger.log.debug(
                "DBI._get_connection.new",
                connection_id=self._connection.connection_id,
                pooled=DBI.connection_pool is not None,
            )
        return self._connection

    def execute(self, sql: str, sql_args: typing.Tuple = ()) -> int:
        """
        For executing CRUD SQL commands.
        INSERT returns last inserted ID
        UPDATE, DELETE returns number of affected rows
        :param sql: SQL command
        :param sql_args: Tuple of positioned SQL arguments. It will safely replace "%s" sequences.
        :return: Number of affexted rows or last inserted ID or False if command failed.
        """
        Logger.log.debug("DBI.execute", sql=sql, sql_args=sql_args)

        ret = False
        cursor = None
        is_insert_command = sql.upper().startswith("INSERT")
        try:
            if self._get_connection().is_connected():
                cursor = self._get_connection().cursor()
                Logger.log.debug("DBI.execute.execute")
                cursor.execute(sql, sql_args)
                self._commit()

                ret = cursor.lastrowid if is_insert_command else cursor.rowcount
        except Error as ex:
            Logger.log.exception("DBI.execute.exception", message=ex)
            raise ex
        finally:
            if self._get_connection().is_connected():
                if cursor:
                    cursor.close()

                self._close_connection()
        return ret

    def execute_many(self, sql: str, sql_args: typing.List[typing.Tuple]) -> int:
        """
        For executing many CRUD SQL commands (Bulk inserts).
        INSERT returns last inserted ID
        UPDATE, DELETE returns number of affected rows
        :param sql: SQL command
        :param sql_args: List of tuples with positional SQL arguments. It will safely replace "%s" sequences.
        :return: Number of affexted rows or last inserted ID or False if command failed.
        """
        Logger.log.debug("DBI.execute_many", sql=sql, sql_args=sql_args)

        ret = False
        cursor = None
        try:
            if self._get_connection().is_connected():
                cursor = self._get_connection().cursor()
                Logger.log.debug("DBI.execute_many.executemany")
                cursor.executemany(sql, sql_args)
                self._commit()

                ret = cursor.rowcount
        except Error as ex:
            Logger.log.exception("DBI.execute_many", message=ex)
            raise ex
        finally:
            if self._get_connection().is_connected():
                if cursor:
                    cursor.close()

                self._close_connection()
        return ret

    def fetch_one(self, sql, sql_args: tuple = (), dictionary_output=True) -> typing.Dict:
        record = None
        cursor = None
        try:
            if self._get_connection().is_connected():
                cursor = self._get_connection().cursor(dictionary=dictionary_output)
                Logger.log.debug("DBI.fetch_one", sql=sql)
                cursor.execute(sql, sql_args)
                record = cursor.fetchone()
        except Error as ex:
            Logger.log.exception("DBI.fetch_one", message=ex)
            raise ex
        finally:
            if self._get_connection().is_connected():
                if cursor:
                    cursor.close()

                self._close_connection()
        return record

    def fetch_all(self, sql, sql_args: tuple = (), dictionary_output=True) -> typing.List[typing.Dict]:
        records = None
        cursor = None
        try:
            if self._get_connection().is_connected():
                cursor = self._get_connection().cursor(dictionary=dictionary_output)
                Logger.log.debug("DBI.fetch_all", sql=sql)
                cursor.execute(sql, sql_args)
                records = cursor.fetchall()

        except Error as ex:
            Logger.log.exception("DBI.fetch_all", message=ex)
            raise ex
        finally:
            if self._get_connection().is_connected():
                if cursor:
                    cursor.close()

                self._close_connection()
        return records

    @classmethod
    def use_self_dbi(cls, dbi_attr_name: str = "dbi"):
        """
        Allow decorated function to work with one instance of DB connection
        :param dbi_attr_name: Name of attribute where DBI instance is stored in self. "dbi" is default.
        """

        def decorator(fnc):
            @wraps(fnc)
            def wrapper(*args, **kwargs):
                class_instance = args[0]
                dbi = class_instance.__getattribute__(dbi_attr_name)
                dbi._is_in_self_dbi = True
                Logger.log.debug("DBI.use_self_dbi.start")
                try:
                    ret = fnc(*args, **kwargs)
                except Exception as ex:
                    raise ex
                finally:
                    dbi._is_in_self_dbi = False
                    Logger.log.debug("DBI.use_self_dbi.done")
                    dbi._close_connection()
                return ret

            return wrapper

        return decorator

    @classmethod
    def pass_dbi(cls, pass_dbi_as: str = "dbi"):
        """
        Pass DBI instasnce into wrapped method
        :param pass_dbi_as: Name of argument for passing DBI instance. "dbi" is default.
        """

        def decorator(fnc):
            @wraps(fnc)
            def wrapper(*args, **kwargs):
                dbi = cls()
                dbi._is_in_pass_dbi = True
                Logger.log.debug("DBI.pass_dbi.start")
                try:
                    kwargs[pass_dbi_as] = dbi
                    ret = fnc(*args, **kwargs)
                except Exception as ex:
                    raise ex
                finally:
                    dbi._is_in_pass_dbi = False
                    Logger.log.debug("DBI.pass_dbi.done")
                    dbi._close_connection()
                return ret

            return wrapper

        return decorator

    @classmethod
    def transaction(cls, pass_dbi_as: str = "dbi"):
        """
        Transaction wrapper

        How to use it:
            @DBI.transaction("dbi")\n
            def run(self, dbi):\n
                dbi.execute("INSERT INTO `table1` (`column1`, `column2`) VALUES ('value1", 44)")\n
                dbi.execute("INSERT INTO `table2` (`column1`, `column2`) VALUES ('value2", 55)")\n
                dbi.execute("INSERT INTO `table3` (`column1`, `column2`) VALUES ('value3", 66)")\n

        How to use it with DataManagers:
            @DBI.transaction("dbi")\n
            def run(self, dbi):\n
                model1 = DataManager.create_model_instance()\n
                model1.number = 14\n
                manager = RegionRegionsManager(dbi=dbi)\n
                manager.insert_one(model1)\n
                model2 = DataManager.create_model_instance()\n
                model2.number = 15\n
                manager.insert_one(mod)\n

        :param pass_dbi_as: Name of argument for passing DBI instance. "dbi" is default.
        """

        def decorator(fnc):
            @wraps(fnc)
            def wrapper(*args, **kwargs):
                dbi = cls()
                dbi._is_in_transaction = True
                Logger.log.debug("DBI.transaction.start")
                dbi._get_connection().start_transaction()
                try:
                    kwargs[pass_dbi_as] = dbi
                    ret = fnc(*args, **kwargs)
                except Exception as ex:
                    Logger.log.exception("DBI.transaction.rollback", message=ex)
                    dbi._get_connection().rollback()
                    raise
                else:
                    dbi._is_in_transaction = False
                    dbi._commit()
                finally:
                    dbi._is_in_transaction = False
                    Logger.log.debug("DBI.transaction.done")
                    dbi._close_connection()
                return ret

            return wrapper

        return decorator

    def _commit(self):
        if not self._is_in_transaction:
            Logger.log.debug("DBI._commit")
            self._connection.commit()
            return True

        return False

    def _close_connection(self):
        if self._is_in_transaction or self._is_in_pass_dbi or self._is_in_self_dbi:
            return True
        try:
            Logger.log.debug("DBI._close_connection", connection_id=self._connection.connection_id)
            self._connection.close()
            self._connection = None
            return True
        except Error as ex:
            Logger.log.exception("DBI._close_connection", message=ex)
        self._connection = None

        return False
