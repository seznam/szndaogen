import typing

from ..tools.log import Logger

from .db import DBI
from .model_base import ModelBase
from ..config import Config


class ManagerException(BaseException):
    pass


class ViewManagerBase:
    MODEL_CLASS = ModelBase

    def __init__(self, dbi: DBI = None):
        """
        Init function of base model manager class
        :param dbi: Instance of database connector. If empty it will be created automatically. Instance of DBI is usualy used with combination of transaction wrapper @DBI.transaction("dbi")
        """
        self.dbi = DBI() if dbi is None else dbi
        self.bulk_insert_buffer_size = 50
        self.bulk_insert_sql_statement = ""
        self.bulk_insert_values_buffer = []

    @classmethod
    def create_model_instance(cls, init_data: dict = None) -> ModelBase:
        if init_data is None:
            init_data = {}

        return cls.MODEL_CLASS(init_data)

    def select_one(
        self,
        *args,
        condition: str = "1",
        condition_params: typing.Tuple = (),
        projection: typing.Tuple = (),
        order_by: typing.Tuple = (),
    ) -> ModelBase:
        """
        Select one row from DB table or View
        :param projection: sql projection - default *
        :param args: Primary keys or condition and condition_params if there are no primary keys
        :param condition: SQL Condition (Will be used if there are no positional args from primary keys)
        :param condition_params: Positional params for SQL condition
            (Will be used if there are no positional args from primary keys)
        :param order_by: Params for SQL order by statement
        """
        base_condition = self.MODEL_CLASS.Meta.SQL_STATEMENT_WHERE_BASE

        if args:
            condition = self._prepare_primary_sql_condition()
            condition_params = args

        projection_statement = ", ".join(projection) if projection else "*"
        order_by_sql_format = ", ".join(order_by)
        limit = 1

        if base_condition == "1":
            where_statement = f"WHERE ({condition})" if condition else ""
        else:
            where_statement = f"WHERE {base_condition} AND ({condition})" if condition else f"WHERE {base_condition}"

        order_by_statement = f"ORDER BY {order_by_sql_format}" if order_by else ""
        limit_statement = f"LIMIT {limit}" if limit else ""

        sql = self.MODEL_CLASS.Meta.SQL_STATEMENT.format(
            PROJECTION=projection_statement,
            WHERE=where_statement,
            ORDER_BY=order_by_statement,
            LIMIT=limit_statement,
            OFFSET="",
        )

        Logger.log.info("ViewManagerBase.select_one.sql", manager=self.__class__.__name__)

        result = self.dbi.fetch_one(sql, condition_params)

        Logger.log.info("ViewManagerBase.select_one.result", result=result, manager=self.__class__.__name__)

        if Config.MANAGER_AUTO_MAP_MODEL_ATTRIBUTES:
            return self.MODEL_CLASS(result).map_model_attributes() if result else None

        return self.MODEL_CLASS(result) if result else None

    def select_all(
        self,
        condition: str = "1",
        condition_params: typing.Tuple = (),
        projection: typing.Tuple = (),
        order_by: typing.Tuple = (),
        limit: int = 0,
        offset: int = 0,
    ) -> typing.List[ModelBase]:
        """
        Select all rows matching the condition
        :param offset: SQL offset
        :param projection: sql projection - default *
        :param condition: SQL condition
        :param condition_params: Positional params for SQL condition
        :param order_by: Params for SQL order by statement
        :param limit: Params for SQL limit statement
        """
        base_condition = self.MODEL_CLASS.Meta.SQL_STATEMENT_WHERE_BASE

        projection_statement = ", ".join(projection) if projection else "*"

        if base_condition == "1":
            where_statement = f"WHERE ({condition})" if condition else ""
        else:
            where_statement = f"WHERE {base_condition} AND ({condition})" if condition else f"WHERE {base_condition}"

        order_by_sql_format = ", ".join(order_by)
        if len(order_by) > 0:
            order_by_statement = f"ORDER BY {order_by_sql_format}"
        else:
            if self.MODEL_CLASS.Meta.SQL_STATEMENT_ORDER_BY_DEFAULT:
                order_by_statement = f"ORDER BY {self.MODEL_CLASS.Meta.SQL_STATEMENT_ORDER_BY_DEFAULT}"
            else:
                order_by_statement = ""

        limit_statement = f"LIMIT {limit}" if limit else ""
        offset_statement = f"OFFSET {offset}" if offset else ""

        sql = self.MODEL_CLASS.Meta.SQL_STATEMENT.format(
            PROJECTION=projection_statement,
            WHERE=where_statement,
            ORDER_BY=order_by_statement,
            LIMIT=limit_statement,
            OFFSET=offset_statement,
        )

        Logger.log.info("ViewManagerBase.select_all.sql", manager=self.__class__.__name__)

        results = self.dbi.fetch_all(sql, condition_params)

        Logger.log.info("ViewManagerBase.select_all.result", result=results, manager=self.__class__.__name__)

        if Config.MANAGER_AUTO_MAP_MODEL_ATTRIBUTES:
            Logger.log.debug("ViewManagerBase.select_all.result.list.automapped")
            return [self.MODEL_CLASS(result).map_model_attributes() for result in results]

        Logger.log.debug("ViewManagerBase.select_all.result.list")
        return [self.MODEL_CLASS(result) for result in results]

    @staticmethod
    def models_into_dicts(result: typing.List[ModelBase]) -> typing.List[typing.Dict]:
        """
        Convert result of select_all into list of dicts
        :param result: List of models
        """
        return [item.to_dict() for item in result]

    @classmethod
    def _prepare_primary_sql_condition(cls):
        args = ["{} = %s".format(primary_key) for primary_key in cls.MODEL_CLASS.Meta.PRIMARY_KEYS]
        return " AND ".join(args)

    @classmethod
    def _prepare_primary_sql_condition_params(cls, model_instance: ModelBase):
        return [model_instance.__getattribute__(attribute_name) for attribute_name in cls.MODEL_CLASS.Meta.PRIMARY_KEYS]


class TableManagerBase(ViewManagerBase):
    def update_one(self, model_instance: ModelBase, exclude_none_values: bool = False, exclude_columns: list = None) -> int:
        """
        Update one database record based on model attributes
        :param model_instance: Model instance
        :param exclude_none_values: You can exclude columns with None value from update statement
        :param exclude_columns: You can exclude columns names from update statement
        :return: Number of affected rows
        """
        exclude_columns = exclude_columns or []
        if not self.MODEL_CLASS.Meta.PRIMARY_KEYS:
            raise ManagerException("Can't update record based on model instance. There are no primary keys specified.")

        set_prepare = []
        set_prepare_params = []
        for attribute_name in self.MODEL_CLASS.Meta.ATTRIBUTE_LIST:
            value = model_instance.__getattribute__(attribute_name)
            if (exclude_none_values and value is None) or attribute_name in exclude_columns:
                continue
            set_prepare.append("`{}` = %s".format(attribute_name))
            set_prepare_params.append(value)

        condition_prepare = self._prepare_primary_sql_condition()
        condition_prepare_params = self._prepare_primary_sql_condition_params(model_instance)

        sql = "UPDATE `{}` SET {} WHERE {} LIMIT 1".format(
            self.MODEL_CLASS.Meta.TABLE_NAME, ", ".join(set_prepare), condition_prepare
        )

        Logger.log.info("TableManagerBase.update_one.sql", manager=self.__class__.__name__)

        result = self.dbi.execute(sql, set_prepare_params + condition_prepare_params)

        Logger.log.info("TableManagerBase.update_one.result", result=result, manager=self.__class__.__name__)

        return result

    def insert_one(
        self,
        model_instance: ModelBase,
        exclude_none_values: bool = False,
        exclude_columns: list = None,
        use_on_duplicate_update_statement: bool = False,
        use_insert_ignore_statement: bool = False,
    ) -> int:
        """
        Insert one record into database based on model attributes
        :param model_instance: Model instance
        :param exclude_none_values: You can exclude columns with None value from insert statement
        :param exclude_columns: You can exclude columns names from insert statement
        :param use_on_duplicate_update_statement: Use ON DUPLICATE KEY UPDATE statement
        :param use_insert_ignore_statement: Use INSERT IGNORE statement
        :return: Last inserted id if it is possible
        """
        exclude_columns = exclude_columns or []
        insert_prepare = []
        insert_prepare_values = []
        insert_prepare_params = []
        update_prepare = []
        for attribute_name in self.MODEL_CLASS.Meta.ATTRIBUTE_LIST:
            value = model_instance.__getattribute__(attribute_name)
            if (exclude_none_values and value is None) or attribute_name in exclude_columns:
                continue
            insert_prepare.append("`{}`".format(attribute_name))
            insert_prepare_values.append("%s")
            insert_prepare_params.append(value)
            if use_on_duplicate_update_statement:
                update_prepare.append("`{0}` = VALUES(`{0}`)".format(attribute_name))

        if use_on_duplicate_update_statement:
            sql = "INSERT INTO `{}` ({}) VALUES ({}) ON DUPLICATE KEY UPDATE {}".format(
                self.MODEL_CLASS.Meta.TABLE_NAME,
                ", ".join(insert_prepare),
                ", ".join(insert_prepare_values),
                ", ".join(update_prepare),
            )
        elif use_insert_ignore_statement:
            sql = "INSERT IGNORE INTO `{}` ({}) VALUES ({})".format(
                self.MODEL_CLASS.Meta.TABLE_NAME, ", ".join(insert_prepare), ", ".join(insert_prepare_values)
            )
        else:
            sql = "INSERT INTO `{}` ({}) VALUES ({})".format(
                self.MODEL_CLASS.Meta.TABLE_NAME, ", ".join(insert_prepare), ", ".join(insert_prepare_values)
            )

        Logger.log.info("TableManagerBase.insert_one.sql", manager=self.__class__.__name__)

        result = self.dbi.execute(sql, insert_prepare_params)

        # set primary key value
        if (
            result
            and len(self.MODEL_CLASS.Meta.PRIMARY_KEYS) == 1
            and self.MODEL_CLASS.Meta.ATTRIBUTE_TYPES[self.MODEL_CLASS.Meta.PRIMARY_KEYS[0]] == int
        ):
            model_instance.__setattr__(self.MODEL_CLASS.Meta.PRIMARY_KEYS[0], result)

        Logger.log.info("TableManagerBase.insert_one.result", result=result, manager=self.__class__.__name__)

        return result

    def insert_one_bulk(
        self,
        model_instance: ModelBase,
        exclude_none_values: bool = False,
        exclude_columns: list = None,
        use_on_duplicate_update_statement: bool = False,
        use_insert_ignore_statement: bool = False,
        auto_flush: bool = True,
    ) -> int:
        """
        Insert more records in one bulk.
        :param model_instance: Model instance
        :param exclude_none_values: You can exclude columns with None value from insert statement
        :param exclude_columns: You can exclude columns names from insert statement
        :param use_on_duplicate_update_statement: Use ON DUPLICATE KEY UPDATE statement
        :param use_insert_ignore_statement: Use INSERT IGNORE statement
        :param auto_flush: Auto flush bulks from buffer after N records (defined in self.bulk_insert_buffer_size)
        :return: Number of items in buffer
        """
        exclude_columns = exclude_columns or []
        insert_prepare = []
        insert_prepare_values = []
        insert_prepare_params = []
        update_prepare = []
        for attribute_name in self.MODEL_CLASS.Meta.ATTRIBUTE_LIST:
            value = model_instance.__getattribute__(attribute_name)
            if (exclude_none_values and value is None) or attribute_name in exclude_columns:
                continue
            insert_prepare.append("`{}`".format(attribute_name))
            insert_prepare_values.append("%s")
            insert_prepare_params.append(value)
            if use_on_duplicate_update_statement:
                update_prepare.append("`{0}` = VALUES(`{0}`)".format(attribute_name))

        if not self.bulk_insert_sql_statement:
            if use_on_duplicate_update_statement:
                self.bulk_insert_sql_statement = "INSERT INTO `{}` ({}) VALUES ({}) ON DUPLICATE KEY UPDATE {}".format(
                    self.MODEL_CLASS.Meta.TABLE_NAME,
                    ", ".join(insert_prepare),
                    ", ".join(insert_prepare_values),
                    ", ".join(update_prepare),
                )
            elif use_insert_ignore_statement:
                self.bulk_insert_sql_statement = "INSERT IGNORE INTO `{}` ({}) VALUES ({})".format(
                    self.MODEL_CLASS.Meta.TABLE_NAME, ", ".join(insert_prepare), ", ".join(insert_prepare_values)
                )
            else:
                self.bulk_insert_sql_statement = "INSERT INTO `{}` ({}) VALUES ({})".format(
                    self.MODEL_CLASS.Meta.TABLE_NAME, ", ".join(insert_prepare), ", ".join(insert_prepare_values)
                )

        self.bulk_insert_values_buffer.append(insert_prepare_params)
        buffer_len = len(self.bulk_insert_values_buffer)
        if auto_flush and buffer_len >= self.bulk_insert_buffer_size:
            self.insert_bulk_flush()

        return buffer_len

    def insert_bulk_flush(self) -> int:
        """
        Flush prepared inserts from buffer
        :return: Number of inserted rows
        """

        result = None
        if self.bulk_insert_values_buffer:
            result = self.dbi.execute_many(self.bulk_insert_sql_statement, self.bulk_insert_values_buffer)

        Logger.log.info(
            "TableManagerBase.insert_one_bulk_flush.result",
            result=result,
            inserted_count=len(self.bulk_insert_values_buffer),
            manager=self.__class__.__name__,
        )

        self.bulk_insert_sql_statement = ""
        self.bulk_insert_values_buffer = []
        return result

    def delete_one(self, model_instance: ModelBase) -> int:
        """
        Delete one row matching primary key condition.
        :param model_instance: Instance of model
        :return: Number of affected rows
        """
        condition_prepare = self._prepare_primary_sql_condition()
        condition_prepare_params = self._prepare_primary_sql_condition_params(model_instance)

        sql_statement = "DELETE FROM  `{}` WHERE {} LIMIT 1"
        sql = sql_statement.format(self.MODEL_CLASS.Meta.TABLE_NAME, condition_prepare)

        Logger.log.info("TableManagerBase.delete_one.sql", manager=self.__class__.__name__)

        result = self.dbi.execute(sql, condition_prepare_params)

        Logger.log.info(f"TableManagerBase.delete_one.result", result=result, manager=self.__class__.__name__)

        return result

    def delete_all(
        self, condition: str, condition_params: typing.Tuple = (), order_by: typing.Tuple = (), limit: int = 0
    ) -> int:
        """
        Delete all table rows matching condition.
        :param condition: SQL condition statement
        :param condition_params: SQL condition position params
        :param order_by: SQL order statement
        :param limit: SQL limit statement
        :return: Number of affected rows
        """
        where_statement = f"WHERE {condition}"
        order_by_sql_format = ", ".join(order_by)
        order_by_statement = f"ORDER BY {order_by_sql_format}" if order_by else ""
        limit_statement = f"LIMIT {limit}" if limit else ""

        sql_statement = "DELETE FROM `{TABLE}` {WHERE} {ORDER_BY} {LIMIT}"
        sql = sql_statement.format(
            TABLE=self.MODEL_CLASS.Meta.TABLE_NAME,
            WHERE=where_statement,
            ORDER_BY=order_by_statement,
            LIMIT=limit_statement,
        )

        Logger.log.info("TableManagerBase.delete_all.sql", manager=self.__class__.__name__)

        result = self.dbi.execute(sql, condition_params)

        Logger.log.info("TableManagerBase.delete_all.result", result=result, manager=self.__class__.__name__)

        return result
