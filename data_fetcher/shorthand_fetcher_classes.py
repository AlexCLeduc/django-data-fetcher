from collections import defaultdict

from .core import InjectableDataFetcher


class AbstractModelByIdFetcher(InjectableDataFetcher):
    model = None  # override this part

    @classmethod
    def batch_load_dict(cls, ids):
        records = list(cls.model.objects.filter(pk__in=ids))
        return {record.id: record for record in records}

    def get_all(self, queryset=None):
        if queryset is None:
            queryset = self.model.objects.all()
        for r in queryset:
            self.prime(r.pk, r)


class PrimaryKeyFetcherFactory:
    """
    This ensures the same _class_ for a single model can only be created once.
    This is because some consumers dynamically create data-fetchers based on models not yet known
    """

    datafetcher_classes_by_model = {}

    @staticmethod
    def _create_datafetcher_cls_for_model(model_cls):
        return type(
            f"{model_cls.__name__}ByIDFetcher",
            (AbstractModelByIdFetcher,),
            dict(model=model_cls),
        )

    @classmethod
    def get_model_by_id_fetcher(cls, model_cls):
        if model_cls in cls.datafetcher_classes_by_model:
            return cls.datafetcher_classes_by_model[model_cls]
        else:
            fetcher = cls._create_datafetcher_cls_for_model(model_cls)
            cls.datafetcher_classes_by_model[model_cls] = fetcher
            return fetcher


class AbstractChildModelByAttrFetcher(InjectableDataFetcher):
    """
    Loads many records by a single attr, use this to create child-by-parent-id loaders
    """

    model = None  # override this part
    attr = None  # override this part

    @classmethod
    def batch_load(cls, attr_values):
        records = list(
            cls.model.objects.filter(**{f"{cls.attr}__in": attr_values})
        )
        by_attr = defaultdict(list)
        for record in records:
            by_attr[getattr(record, cls.attr)].append(record)

        return [by_attr[attr_val] for attr_val in attr_values]
