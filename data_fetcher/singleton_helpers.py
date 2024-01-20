from functools import wraps

from .core import InjectableDataFetcher
from .util import MissingRequestContextException, get_request_bound_fetcher


class SingletonDataFetcher(InjectableDataFetcher):
    """
    shortcut for data-fetcher that always return the same value,
    e.g. the most-recent record in a table
    """

    def fetch_single_value(self):
        raise NotImplementedError("must implement get_value")

    def get_value(self):
        if "1" not in self._cache:
            self._cache["1"] = self.fetch_single_value()
        return self._cache["1"]

    def get(self, key):
        raise TypeError(
            "SingletonDataFetcher does not support get or get_many"
        )

    def get_many(self, keys):
        raise TypeError(
            "SingletonDataFetcher does not support get or get_many"
        )


def request_cached_value(fn):
    """
    Decorator for datafetchers that are only used in a single request
    """

    class FetcherForFunction(SingletonDataFetcher):
        def fetch_single_value(self):
            return fn()

    @wraps(fn)
    def wrapper():
        try:
            return get_request_bound_fetcher(FetcherForFunction).get_value()
        except MissingRequestContextException:
            print(
                f"WARNING: calling {fn.__name__} outside of a request context,"
                " caching is disabled"
            )
            return fn()

    return wrapper
