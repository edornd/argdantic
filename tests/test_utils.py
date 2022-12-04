import logging
import typing as types

from argdantic.utils import is_container, is_mapping, is_multiple, is_typing

LOG = logging.getLogger(__name__)


def test_registry_set():
    from argdantic.registry import Registry

    registry = Registry()
    registry["foo"] = "bar"
    assert registry.store == {"foo": "bar"}


def test_registry_get():
    from argdantic.registry import Registry

    registry = Registry()
    registry["foo"] = "bar"
    assert registry["foo"] == "bar"


def test_registry_get_missing():
    from argdantic.registry import Registry

    registry = Registry()
    result = registry["foo"]
    assert result is None


def test_registry_length():
    from argdantic.registry import Registry

    registry = Registry()
    assert len(registry) == 0
    registry["foo"] = "bar"
    assert len(registry) == 1
    registry["bar"] = "baz"
    assert len(registry) == 2
    del registry["foo"]
    assert len(registry) == 1
    del registry["bar"]
    assert len(registry) == 0


def test_registry_iterate():
    from argdantic.registry import Registry

    registry = Registry()
    registry["foo"] = "bar"
    registry["bar"] = "baz"
    assert list(registry) == ["foo", "bar"]


def test_is_multiple():
    assert is_multiple(list) is True
    assert is_multiple(tuple) is True
    assert is_multiple(range) is True
    assert is_multiple(dict) is False
    assert is_multiple(int) is False
    assert is_multiple(str) is False
    assert is_multiple(bytes) is False
    assert is_multiple(float) is False
    assert is_multiple(bool) is False
    assert is_multiple(None) is False
    assert is_multiple(object) is False
    assert is_multiple(type) is False
    assert is_multiple(types.Generic) is False
    assert is_multiple(types.Sequence) is True
    assert is_multiple(types.Sequence[int]) is True
    assert is_multiple(types.List) is True
    assert is_multiple(types.Tuple[str]) is True


def test_is_container():
    assert is_container(list) is True
    assert is_container(tuple) is True
    assert is_container(range) is True
    assert is_container(dict) is True
    assert is_container(int) is False
    assert is_container(str) is False
    assert is_container(bytes) is False
    assert is_container(float) is False
    assert is_container(bool) is False
    assert is_container(None) is False
    assert is_container(object) is False
    assert is_container(type) is False
    assert is_container(types.Generic) is False
    assert is_container(types.Sequence) is True
    assert is_container(types.Sequence[int]) is True
    assert is_container(types.List) is True
    assert is_container(types.Tuple[str]) is True
    assert is_container(types.Mapping) is True


def test_is_mapping():
    assert is_mapping(list) is False
    assert is_mapping(tuple) is False
    assert is_mapping(range) is False
    assert is_mapping(dict) is True
    assert is_mapping(int) is False
    assert is_mapping(str) is False
    assert is_mapping(bytes) is False
    assert is_mapping(float) is False
    assert is_mapping(bool) is False
    assert is_mapping(None) is False
    assert is_mapping(object) is False
    assert is_mapping(type) is False
    assert is_mapping(types.Generic) is False
    assert is_mapping(types.Sequence) is False
    assert is_mapping(types.Sequence[int]) is False
    assert is_mapping(types.List) is False
    assert is_mapping(types.Tuple[str]) is False
    assert is_mapping(types.Mapping) is True
    assert is_mapping(types.Mapping[str, int]) is True
    assert is_mapping(types.Dict) is True


def test_is_typing():
    assert is_typing(list) is False
    assert is_typing(tuple) is False
    assert is_typing(range) is False
    assert is_typing(dict) is False
    assert is_typing(int) is False
    assert is_typing(str) is False
    assert is_typing(bytes) is False
    assert is_typing(float) is False
    assert is_typing(bool) is False
    assert is_typing(None) is False
    assert is_typing(object) is False
    assert is_typing(type) is False
    assert is_typing(types.Type) is True
    assert is_typing(types.List[types.Set[str]]) is False
