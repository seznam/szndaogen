import pytest

from .auto_group import auto_group_dict
from .auto_group import auto_group_list
from .auto_group import auto_group_list_by_pkeys

_input1 = [
    {"a": 1, "b": 2, "c__a": 33, "c__b": 44},
    {"a": 1, "b": 2, "c__a": 55, "c__b": 66},
    {"a": 2, "b": 2, "c__a": 7, "c__b": 88},
    {"a": 2, "b": 2, "c__a": 77, "c__b": 99},
]
_expected1_1 = {
    "1": {"a": 1, "b": 2, "c": [{"a": 33, "b": 44}, {"a": 55, "b": 66}]},
    "2": {"a": 2, "b": 2, "c": [{"a": 7, "b": 88}, {"a": 77, "b": 99}]},
}
_expected1_2 = {
    "1-2": {"a": 1, "b": 2, "c": [{"a": 33, "b": 44}, {"a": 55, "b": 66}]},
    "2-2": {"a": 2, "b": 2, "c": [{"a": 7, "b": 88}, {"a": 77, "b": 99}]},
}

auto_group_list_by_pkeys_input = [(("a",), _input1, _expected1_1), (("a", "b"), _input1, _expected1_2)]


@pytest.mark.parametrize("primary_key_names, input, expected", auto_group_list_by_pkeys_input)
def test_auto_group_list_by_pkeys(primary_key_names, input, expected):
    assert auto_group_list_by_pkeys(primary_key_names, input) == expected


_input2 = [
    {"a": 1, "b": 2, "c__a": 3, "c__b": 4},
    {"a": 1, "b": 2, "c__a": 5, "c__b": 6},
    {"a": 1, "b": 2, "c__a": 7, "c__b": 8},
]
_expected2 = {"a": 1, "b": 2, "c": [{"a": 3, "b": 4}, {"a": 5, "b": 6}, {"a": 7, "b": 8}]}
auto_group_list_input = [(_input2, _expected2)]


@pytest.mark.parametrize("input, expected", auto_group_list_input)
def test_auto_group_list(input, expected):
    assert auto_group_list(input) == expected


_input3 = {"a": 1, "b": 2, "c___a": 3, "c___b___bb": 4, "c___b___cc": 5}
_expected3 = {"a": 1, "b": 2, "c": {"a": 3, "b": {"bb": 4, "cc": 5}}}

auto_group_dict_input = [(_input3, _expected3)]


@pytest.mark.parametrize("input, expected", auto_group_dict_input)
def test_auto_group_dict(input, expected):
    assert auto_group_dict(input) == expected
