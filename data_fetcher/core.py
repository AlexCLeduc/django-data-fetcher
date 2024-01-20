from collections import defaultdict



class BaseDataFetcher:
    def __init__(self):
        self._cache = {}

    def get(self, key):
        if key not in self._cache:
            return self._get_single_uncached_value(key)
        return self._cache[key]

    def get_many(self, keys):
        uncached_keys = [key for key in keys if key not in self._cache]
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


class InjectableDataFetcher(BaseDataFetcher):
    """
    Factory for creating composable datafetchers
    must pass a dict-like instance cache to the constructor
    """

    datafetcher_instance_cache = None

    def __new__(cls, datafetcher_instance_cache):
        if cls not in datafetcher_instance_cache:
            datafetcher_instance_cache[cls] = super().__new__(cls)
        fetcher = datafetcher_instance_cache[cls]
        assert isinstance(fetcher, cls)
        return fetcher

    def __init__(self, datafetcher_instance_cache):
        if self.datafetcher_instance_cache != datafetcher_instance_cache:
            self.datafetcher_instance_cache = datafetcher_instance_cache
            super().__init__()


