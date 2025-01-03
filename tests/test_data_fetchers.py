import datetime
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model

from data_fetcher import (
    DataFetcher,
    PrimaryKeyFetcherFactory,
    get_datafetcher_request_cache,
)
from data_fetcher.util import GlobalRequest, get_request


def test_global_request_outside_request():
    assert get_request() is None


def test_global_request_context_processor():
    with GlobalRequest():
        assert get_request() is not None
        get_request().x = 1
        assert get_request().x == 1


def test_global_request_returns_same_request():
    with GlobalRequest():
        r1 = get_request()
        r2 = get_request()
        assert r1 is r2
    with GlobalRequest():
        r3 = get_request()

    assert r1 is not r3


def test_user_datafetcher(django_assert_num_queries):
    users = [
        get_user_model().objects.create(username=f"test_user_{i}")
        for i in range(10)
    ]
    user_ids = [user.id for user in users]

    UserByPKFetcher = PrimaryKeyFetcherFactory.get_model_by_id_fetcher(
        get_user_model()
    )

    with GlobalRequest():
        loader = UserByPKFetcher.get_instance()
        with django_assert_num_queries(1):
            # querying users also prefetches groups, so 2 queries are expected
            assert loader.get_many(user_ids) == users
            assert loader.get(user_ids[0]) == users[0]
            assert loader.get_many_as_dict(user_ids) == {
                user.id: user for user in users
            }

        loader2 = UserByPKFetcher.get_instance()
        assert loader is loader2

    with GlobalRequest():
        # now check a new loader is brand new w/out any cache
        loader3 = UserByPKFetcher.get_instance()
        assert loader != loader3
        assert loader3._cache == {}


def test_composed_datafetcher(django_assert_max_num_queries):
    users = [
        get_user_model().objects.create(username=f"test_user_{i}")
        for i in range(10)
    ]
    user_ids = [user.id for user in users]

    UserByPKFetcher = PrimaryKeyFetcherFactory.get_model_by_id_fetcher(
        get_user_model()
    )

    spy = MagicMock()

    # Trivial example of dataloader composition
    class TrivialOtherFetcher(DataFetcher):
        def batch_load_dict(self, keys):
            spy(keys)
            user_fetcher = UserByPKFetcher.get_instance()
            return user_fetcher.get_many_as_dict(keys)

    with GlobalRequest():
        loader = TrivialOtherFetcher.get_instance()
        with django_assert_max_num_queries(1):
            # querying users also prefetches groups, so 2 queries are expected
            assert loader.get_many(user_ids) == users
            assert loader.get(user_ids[0]) == users[0]
            assert loader.get_many_as_dict(user_ids) == {
                user.id: user for user in users
            }

        assert spy.call_count == 1

        fetcher_cache = get_datafetcher_request_cache()
        assert fetcher_cache[UserByPKFetcher] is not None


def test_priming():
    with GlobalRequest():
        user_fetcher = PrimaryKeyFetcherFactory.get_model_by_id_fetcher(
            get_user_model()
        ).get_instance()

        user_fetcher.prime(1, "test value")
        assert user_fetcher.get(1) == "test value"


def test_pk_fetcher_fetch_all(django_assert_max_num_queries):
    users = [
        get_user_model().objects.create(username=f"test_user_{i}")
        for i in range(10)
    ]
    u1 = users[0]
    user_ids = [user.id for user in users]

    user_fetcher = PrimaryKeyFetcherFactory.get_model_by_id_fetcher(
        get_user_model()
    ).get_instance()

    with GlobalRequest():
        with django_assert_max_num_queries(1):
            records = user_fetcher.get_all()
            assert set(records) == set(users)
            u = user_fetcher.get(user_ids[0])
            assert u == u1


def test_batch_load_dict_none_value():
    """
    the batch_load_dict is more tolerant than the list counterpart,
    it doesn't need explicit None

    Also check that ommitted keys still get cached
    """

    spy = MagicMock()

    class TestFetcher(DataFetcher):
        def batch_load_dict(self, keys):
            spy()
            return {"a": 1, "b": None}

    with GlobalRequest():
        fetcher = TestFetcher.get_instance()

        fetcher.prefetch_keys(["a", "b", "c"])
        assert fetcher.get("a") == 1
        assert fetcher.get("b") is None
        assert fetcher.get("c") is None

        assert spy.call_count == 1


def test_queued_fetch():
    spy = MagicMock()

    class TestFetcher(DataFetcher):
        def batch_load_dict(self, keys):
            spy(keys)
            return {key: key * 2 for key in keys}

    with GlobalRequest():
        fetcher = TestFetcher.get_instance()
        fetcher.prime(1, 2)

        fetcher.enqueue_keys([1, 2, 3, 4])

        assert fetcher.get(1) == 2
        assert fetcher.get(2) == 4
        assert fetcher.get(3) == 6
        assert fetcher.get_many([2, 4, 5]) == [4, 8, 10]

        # primed/cached keys should not be called, even if enqueued
        assert spy.call_args_list == [
            (([2, 3, 4],),),
            (([5],),),
        ]

        # now check a regular .get() will also fetch queued keys
        fetcher.enqueue_keys([10, 11])
        assert fetcher.get(12) == 24
        assert fetcher.get(10) == 20
        assert spy.call_args_list == [
            (([2, 3, 4],),),
            (([5],),),
            (([10, 11, 12],),),
        ]

        # and clears cache
        fetcher.fetch_queued()
        assert spy.call_count == 3


def test_fetch_lazy():
    spy = MagicMock()

    class TestFetcher(DataFetcher):
        def batch_load_dict(self, keys):
            spy(keys)
            return {key: key * 2 for key in keys}

    with GlobalRequest():
        fetcher = TestFetcher.get_instance()

        # check lazy calls are flushed all at once
        l1 = fetcher.get_lazy(1)
        l2 = fetcher.get_lazy(2)
        l3 = fetcher.get_lazy(3)
        assert spy.call_count == 0

        assert l3.get() == 6
        assert spy.call_count == 1
        spy.assert_called_once_with([1, 2, 3])

        # and that queue is cleared
        fetcher.fetch_queued()
        assert spy.call_count == 1
        spy.assert_called_once_with([1, 2, 3])

        # and similarly for get_many_lazy
        l4_5 = fetcher.get_many_lazy([4, 5])
        spy.assert_called_once_with([1, 2, 3])
        l4_5.get()

        assert spy.call_count == 2
        assert spy.call_args_list == [
            (([1, 2, 3],),),
            (([4, 5],),),
        ]
