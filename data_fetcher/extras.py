from functools import cache, wraps

from .core import InjectableDataFetcher
from .util import MissingRequestContextException, get_datafetcher_request_cache


def cache_within_request(fn):
    """
    ensure a function's values are cached for the duration of a request

    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            datafetcher_cache = get_datafetcher_request_cache()
        except MissingRequestContextException:
            print(
                f"WARNING: calling {fn.__name__} outside of a request context,"
                " caching is disabled"
            )
            return fn(*args, **kwargs)

        # use function itself as key
        if fn not in datafetcher_cache:
            datafetcher_cache[fn] = cache(fn)

        return datafetcher_cache[fn](*args, **kwargs)

    return wrapper


class ValueBoundFetcherFactory:
    datafetcher_classes_by_key = {}

    @staticmethod
    def _create_datafetcher_cls_for_keyval(
        parent_cls,
        key,
        value=None,
    ):
        if value is None:
            value = key

        return type(
            f"{parent_cls.__name__}__{key}",
            (parent_cls,),
            dict(
                bound_value=value,
            ),
        )

    @classmethod
    def get_fetcher_by_key(cls, parent_cls, key, value=None):
        """
        This ensures the same _class_ for a single key can only be created once

        datafetcher class will 'provide'
        the value. If key matches an already generated class, returns that class

        value argument only necessary if you want attach an hashable value
        """

        dict_key = (parent_cls, key)

        if dict_key in cls.datafetcher_classes_by_key:
            return cls.datafetcher_classes_by_key[dict_key]
        else:
            fetcher = cls._create_datafetcher_cls_for_keyval(
                parent_cls, key, value
            )
            cls.datafetcher_classes_by_key[dict_key] = fetcher
            return fetcher


class ValueBoundDataFetcher(InjectableDataFetcher):
    """
    To be used as a parent class for keyed-datafetchers

    The most common use case for ValueBoundDataFetcher
    is providing a user_id to a data-fetcher

    """

    def __init__(self, *args, **kwargs):
        if not getattr(self, "bound_value", None):
            raise MissingRequestContextException(
                "AbstractThreatLocationAsOfTimeByThreatIdFetcher "
                "must be instantiated  KeyedDataFetcherFactory"
            )
        super().__init__(*args, **kwargs)

    @classmethod
    def get_value_bound_class(cls, key, value=None):
        """
        if value not hashable, provide key first, then value
        otherwise just provide the value as 'key'
        """
        return ValueBoundFetcherFactory.get_fetcher_by_key(
            cls, key, value=None
        )
