from collections import defaultdict

from .util import MissingRequestContextException, get_datafetcher_request_cache


class BaseDataFetcher:
    def __init__(self):
        self._cache = {}
        self._queue = set()

    def get(self, key):
        all_keys = {key, *self._queue}

        self.prefetch_keys(all_keys)

        return self._cache[key]

    def get_many(self, keys):
        all_keys = {*keys, *self._queue}

        uncached_keys = [key for key in all_keys if key not in self._cache]
        if uncached_keys:
            self._get_many_uncached_values(uncached_keys)

        return [self._cache.get(key) for key in keys]

    def prefetch_keys(self, keys):
        self.get_many(keys)

    def get_many_as_dict(self, keys):
        return dict(zip(keys, self.get_many(keys)))

    def _get_single_uncached_value(self, key):
        return self.batch_load_and_cache([key])[0]

    def _get_many_uncached_values(self, keys):
        return self.batch_load_and_cache(keys)

    def _batch_load_fn(self, keys):
        if getattr(self, "batch_load", None):
            return self.batch_load(keys)
        elif getattr(self, "batch_load_dict", None):
            value_dict = self.batch_load_dict(keys)
            return [value_dict.get(key) for key in keys]
        else:
            raise NotImplementedError(
                "must implement batch_load or batch_load_dict"
            )

    def batch_load_and_cache(self, keys):
        values = self._batch_load_fn(keys)
        for key, value in zip(keys, values):
            self._cache[key] = value
        return values

    def prime(self, key, value):
        self._cache[key] = value

    def enqueue_keys(self, keys):
        self._queue.update(set(keys))

    def fetch_queued(self):
        queued_keys = set(self._queue)
        self.get_many(queued_keys)

    def get_lazy(self, key):
        self.enqueue_keys([key])
        return LazyFetchedValue(lambda: self.get(key))

    def get_many_lazy(self, keys):
        self.enqueue_keys(keys)
        return LazyFetchedValue(lambda: self.get_many(keys))


class LazyFetchedValue:
    def __init__(self, get_val):
        self.get_val = get_val

    def get(self):
        return self.get_val()


class DataFetcher(BaseDataFetcher):
    """
    Factory for creating composable datafetchers
    """

    # this variable can be used for composition
    datafetcher_instance_cache = None

    __create_key = object()

    def __init__(self, create_key):
        # Hacky way to make constructor "private"
        assert (
            create_key == DataFetcher.__create_key
        ), "Never create data-fetcher instances directly, use get_instance"

        super().__init__()

    @classmethod
    def get_instance(cls, raise_on_no_context=False):
        try:
            fetcher_instance_cache = get_datafetcher_request_cache()
        except MissingRequestContextException as e:
            if raise_on_no_context:
                raise e
            else:
                fetcher_instance_cache = {}

        if cls not in fetcher_instance_cache:
            fetcher_instance_cache[cls] = cls(DataFetcher.__create_key)

        return fetcher_instance_cache[cls]
