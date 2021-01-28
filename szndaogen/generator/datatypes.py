DATATYPES = {
    "__default__": ("str", None, "str", '"', '"'),
    "bigint": ("int", None, None, "", ""),
    "bit": ("int", None, None, "", ""),
    "blob": ("bytes", None, None, '"', '"'),
    "mediumblob": ("bytes", None, None, '"', '"'),
    "enum": ("str", None, None, '"', '"'),
    "float": ("float", None, None, "", ""),
    "decimal": ("float", None, "float", "", ""),
    "date": ("datetime.datetime", "datetime", None, 'datetime.datetime.strptime("', '", "%Y-%m-%d")'),
    "datetime": ("datetime.datetime", "datetime", None, 'datetime.datetime.strptime("', '", "%Y-%m-%d %H:%M:%S")'),
    "double": ("float", None, None, "", ""),
    "int": ("int", None, None, "", ""),
    "smallint": ("int", None, None, "", ""),
    "text": ("str", None, None, '"', '"'),
    "mediumtext": ("str", None, None, '"', '"'),
    "timestamp": ("datetime.datetime", "datetime", None, "None  # ", ""),
    "varbinary": ("str", None, None, '"', '"'),
    "varchar": ("str", None, None, '"', '"'),
    "tinyint": ("int", None, None, "", ""),
}
"""
Datatypes structure:
"DBDataType": (
    ModelDataType,
    NeededImport,
    NeededPostConvertFunction,
    LeftWrapperForDefaultValue,
    RightWrapperForDefaultValue)
Because jSON serializer can't easily convert all database types for example 'decimal', it should be converted into float by postprocess on Model side.
"""