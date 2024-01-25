import datetime

from data_fetcher import GlobalRequest, ValueBoundDataFetcher


def test_keyed_datafetcher_factory():
    class DatetimeBoundDataFetcher(ValueBoundDataFetcher):
        bound_value = None

        def batch_load_dict(self, keys):
            return {key: (1, self.bound_value) for key in keys}

    dt1 = datetime.datetime(2021, 1, 1)
    dt2 = datetime.datetime(2021, 1, 2)

    cls1 = DatetimeBoundDataFetcher.get_value_bound_class(dt1)
    cls2 = DatetimeBoundDataFetcher.get_value_bound_class(dt2)
    cls3 = DatetimeBoundDataFetcher.get_value_bound_class(dt1)
    assert cls1 is not cls2
    assert cls1 is cls3

    with GlobalRequest():
        loader_for_cls1 = cls1.get_instance()
        loader_for_cls2 = cls2.get_instance()
        loader_for_cls3 = cls3.get_instance()
        assert loader_for_cls1 is not loader_for_cls2
        assert loader_for_cls1 is loader_for_cls3
