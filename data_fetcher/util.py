from django_middleware_global_request import get_request

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


def get_request_bound_fetcher(dataloader_cls):
    return dataloader_cls(get_datafetcher_request_cache())


def clear_datafetchers():
    """
    Clears all cached values for datafetchers

    Only necessary when a request wants data it has modified
    """
    request = get_request()
    if request and hasattr(request, "datafetcher_cache"):
        # reset the cache to an empty dict
        request.datafetcher_cache = {}


def get_request_bound_user_fetcher_with_fallback(dataloader_cls):
    try:
        return dataloader_cls(get_datafetcher_request_cache())
    except MissingRequestContextException:
        print(
            "WARNING: calling datafetcher outside of a request context, using non-batching fallback"
        )
        return dataloader_cls({})

