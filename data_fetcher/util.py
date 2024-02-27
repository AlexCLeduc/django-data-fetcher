# from data_fetcher.middleware import get_request
from .global_request_context import GlobalRequest, get_request


class MissingRequestContextException(Exception):
    pass


def get_datafetcher_request_cache():
    request = get_request()
    if not request:
        raise MissingRequestContextException(
            "No request is available, don't use datafetchers outside of a request context"
        )

    if not hasattr(request, "datafetcher_cache"):
        request.datafetcher_cache = {}

    return request.datafetcher_cache


def clear_request_caches():
    """
    Clears all cached values for datafetchers

    Only necessary when a request wants data it has modified

    Also clears the functions cached with cache_within_request decorator
    """
    request = get_request()
    if request and hasattr(request, "datafetcher_cache"):
        # reset the cache to an empty dict
        request.datafetcher_cache = {}


def clear_datafetchers():
    """
    clears request cache
    old API, prefer clear_request_caches()
    """
    clear_request_caches()
