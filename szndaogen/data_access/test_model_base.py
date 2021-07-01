import typing

from .model_base import ModelBase


class TModel(ModelBase):
    class Meta:
        TABLE_NAME: str = "table"
        TABLE_TYPE: str = "BASE TABLE"
        # fmt: off
        SQL_STATEMENT: str = "SELECT {PROJECTION} FROM `table` {WHERE} {ORDER_BY} {LIMIT} {OFFSET}"
        # fmt: on

        SQL_STATEMENT_WHERE_BASE: str = "1"
        SQL_STATEMENT_ORDER_BY_DEFAULT: str = ""

        PRIMARY_KEYS: typing.List = ["id", ]
        ATTRIBUTE_LIST: typing.List = ["id", "name", ]
        ATTRIBUTE_TYPES: typing.Dict = {
            "id": int,
            "name": str,
        }
        MODEL_DATA_CONVERTOR: typing.Dict = {
        }

    def __init__(self, init_data: typing.Dict = {}):
        super().__init__(init_data)
        self.id: int = None
        """Type: int(11), Can be NULL: NO, Key: PRI"""
        self.name: str = None
        """Type: varchar(50), Can be NULL: NO"""


def test_model_dataflow():
    model = TModel()
    model.id = 1
    model.name = "total_name"
    assert model.to_dict() == {"id": 1, "name": "total_name"}


def test_model_map_model_attributes():
    model = TModel()
    model.map_model_attributes({"id": 1, "name": "total_name"})
    assert model.id == 1
    assert model.name == "total_name"


def test_model_clone():
    model = TModel()
    model.id = 1
    model.name = "total_name"

    model_clone = model.clone()
    assert model_clone.id == model.id
    assert model_clone.name == model.name
    assert model_clone.to_dict() == model.to_dict()
