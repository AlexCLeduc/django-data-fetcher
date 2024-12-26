import datetime
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model

import pytest

from data_fetcher import cache_within_request, get_datafetcher_request_cache
from data_fetcher.extras import CacheDecoratorException
from data_fetcher.util import GlobalRequest, get_request


def test_cache_decorator():
    spy = MagicMock()

    def func_to_cache():
        spy()
        return 1

    cached_func = cache_within_request(func_to_cache)

    with GlobalRequest():
        result = cached_func()
        result2 = cached_func()

        assert result == result2 == 1
        spy.assert_called_once()

    with GlobalRequest():
        cached_func()
        cached_func()

        assert spy.call_count == 2


def test_cache_with_staticmethod():
    """
    static decorator works in either order
    """

    spy = MagicMock()

    class TestClass:

        @cache_within_request
        @staticmethod
        def _things_by_id():
            spy()
            return {
                1: "a",
                2: "b",
            }

        @staticmethod
        @cache_within_request
        def get_thing(id):
            return TestClass._things_by_id()[id]

    with GlobalRequest():
        assert TestClass.get_thing(1) == "a"
        assert TestClass.get_thing(2) == "b"
        assert TestClass.get_thing(1) == "a"
        assert TestClass.get_thing(2) == "b"
        dict_one = TestClass._things_by_id()
        assert spy.call_count == 1

    with GlobalRequest():
        dict_two = TestClass._things_by_id()

    assert dict_one is not dict_two


def test_cache_with_undecorated_method():
    """obviously not recommended, but it should work"""

    spy = MagicMock()

    class TestClass:

        @cache_within_request
        def _things_by_id():
            spy()
            return {
                1: "a",
                2: "b",
            }

        def get_thing(id):
            return TestClass._things_by_id()[id]

    with GlobalRequest():
        dict_one = TestClass._things_by_id()

        assert TestClass.get_thing(1) == "a"
        assert TestClass.get_thing(2) == "b"
        assert TestClass.get_thing(1) == "a"
        assert TestClass.get_thing(2) == "b"
        assert spy.call_count == 1

    with GlobalRequest():
        dict_two = TestClass._things_by_id()

    assert dict_one is not dict_two


def test_classmethod_correct_order():

    inner_spy = MagicMock()
    spy = MagicMock()

    class TestClass:

        _cls_value = "c"

        @classmethod
        @cache_within_request
        def _other_value(cls):
            inner_spy()
            return cls._cls_value

        @classmethod
        @cache_within_request
        def _things_by_id(cls):
            spy()
            return {
                1: "a",
                2: "b",
                3: cls._other_value(),
            }

        @classmethod
        def get_thing(cls, id):
            return cls._things_by_id()[id]

    with GlobalRequest():
        assert TestClass.get_thing(1) == "a"
        assert TestClass.get_thing(2) == "b"
        assert TestClass.get_thing(1) == "a"
        assert TestClass.get_thing(2) == "b"
        assert TestClass.get_thing(3) == "c"
        dict_one = TestClass._things_by_id()
        assert inner_spy.call_count == 1
        assert spy.call_count == 1

    with GlobalRequest():
        assert TestClass.get_thing(1) == "a"
        assert TestClass.get_thing(2) == "b"
        assert TestClass.get_thing(3) == "c"
        dict_two = TestClass._things_by_id()
        assert inner_spy.call_count == 2
        assert spy.call_count == 2

    assert dict_one is not dict_two


def test_classmethod_wrong_order():

    with pytest.raises(CacheDecoratorException):

        class TestClass:

            @cache_within_request
            @classmethod
            def _other_value(cls):
                pass
