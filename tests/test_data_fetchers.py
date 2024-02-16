import datetime
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model

from django_middleware_global_request import GlobalRequest, get_request

from data_fetcher import (
    InjectableDataFetcher,
    PrimaryKeyFetcherFactory,
    cache_within_request,
    get_datafetcher_request_cache,
)


def test_global_request_outside_request():
    assert get_request() is None


def test_global_request_context_processor():
    with GlobalRequest():
        assert get_request() is not None
        get_request().x = 1
        assert get_request().x == 1


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
    class TrivialOtherFetcher(InjectableDataFetcher):
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


def test_cache_decorator(django_assert_max_num_queries):
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
            user_fetcher.get_all()
            u = user_fetcher.get(user_ids[0])
            assert u == u1
