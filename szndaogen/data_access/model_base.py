import typing


class ModelBase:
    """
    Base model class
    """

    class Meta:
        TABLE_NAME: str = None
        TABLE_TYPE: str = None
        SQL_STATEMENT: str = None
        SQL_STATEMENT_WHERE_BASE: str = None
        SQL_STATEMENT_ORDER_BY_DEFAULT: str = ""
        PRIMARY_KEYS: typing.List = []
        ATTRIBUTE_LIST: typing.List = []
        ATTRIBUTE_TYPES: typing.Dict = {}
        MODEL_DATA_CONVERTOR: typing.Dict = {}

    DATATYPES_CONVERTOR = {"<class 'decimal.Decimal'>": float}

    def __init__(self, init_data: typing.Dict = {}):
        self.model_data: typing.Dict = self._convert_datatypes(init_data)

    def __str__(self):
        return str(self.model_data)

    def __setattr__(self, key, value):
        if key in self.Meta.ATTRIBUTE_LIST and hasattr(self, "model_data"):
            self.model_data[key] = value
        return super().__setattr__(key, value)

    def to_dict(self) -> typing.Dict:
        """
        Returns internal model data as dict
        """
        return self.model_data

    def map_model_attributes(self, data: typing.Dict = None) -> "ModelBase":
        """
        Set or update model attributes by internal model data or external data from method param if attribute exists.
        :param data: External data to be mapped
        """
        if data is None:
            data = self.model_data
        for key, value in data.items():
            if key in self.Meta.ATTRIBUTE_LIST:
                self.__setattr__(key, value)
        return self

    def clone(self):
        model_clone = self.__class__()
        for attribute_name in self.Meta.ATTRIBUTE_LIST:
            model_clone.__setattr__(attribute_name, self.__getattribute__(attribute_name))
            model_clone.model_data = self.model_data.copy()
        return model_clone

    @classmethod
    def _convert_datatypes(cls, item: dict) -> dict:
        for key, value in item.items():
            datatype = str(type(value))
            # some known problematic data types need to be converted for easy jSON transform
            if datatype in cls.DATATYPES_CONVERTOR:
                item[key] = cls.DATATYPES_CONVERTOR[datatype](value)
            # data convertion for DB type
            if key in cls.Meta.MODEL_DATA_CONVERTOR:
                try:
                    item[key] = cls.Meta.MODEL_DATA_CONVERTOR[key](value)
                except Exception as _:
                    item[key] = value  # Conversion failed, pass value unchanged
        return item
