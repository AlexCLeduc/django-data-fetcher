import datetime

from data_fetcher import GlobalRequest
from data_fetcher.extras import (
    AbstractKeyedDataFetcher,
    KeyedDataFetcherFactory,
)


def test_keyed_datafetcher_factory():
    class DatetimeBoundDataFetcher(AbstractKeyedDataFetcher):
        provided_value = None

        def batch_load_dict(self, keys):
            return {key: (1, self.provided_value) for key in keys}

    dt1 = datetime.datetime(2021, 1, 1)
    dt2 = datetime.datetime(2021, 1, 2)

    cls1 = KeyedDataFetcherFactory.get_fetcher_by_key(
        DatetimeBoundDataFetcher, dt1
    )
    cls2 = KeyedDataFetcherFactory.get_fetcher_by_key(
        DatetimeBoundDataFetcher, dt2
    )
    cls3 = KeyedDataFetcherFactory.get_fetcher_by_key(
        DatetimeBoundDataFetcher, dt1
    )
    assert cls1 is not cls2
    assert cls1 is cls3

    with GlobalRequest():
        loader_for_cls1 = cls1.get_instance()
        loader_for_cls2 = cls2.get_instance()
        loader_for_cls3 = cls3.get_instance()
        assert loader_for_cls1 is not loader_for_cls2
        assert loader_for_cls1 is loader_for_cls3
