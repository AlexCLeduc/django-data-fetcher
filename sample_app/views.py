from django.http.response import HttpResponse

from asgiref.sync import sync_to_async

from data_fetcher import PrimaryKeyFetcherFactory

from .models import Author, Book, Tag


def edit_book(request, pk=None):
    book = Book.objects.get(pk=pk)
    if request.POST:
        new_name = request.POST["title"]
        book.title = new_name
        book.save()

    return HttpResponse()


def spyable_func(*args, **kwargs):
    # for testing purposes
    return None


AuthorByIdFetcher = PrimaryKeyFetcherFactory.get_model_by_id_fetcher(Author)


class WatchedAuthorByIdFetcher(AuthorByIdFetcher):
    def batch_load_dict(self, keys):
        spyable_func(keys)
        return super().batch_load_dict(keys)


def get_author(author_id):
    return WatchedAuthorByIdFetcher.get_instance().get(author_id)


def view_with_loaders(request):
    author_ids = Author.objects.values_list("id", flat=True)
    all_authors = WatchedAuthorByIdFetcher.get_instance().get_many(author_ids)

    for author in all_authors:
        refetched_author = get_author(author.id)
        assert refetched_author is author

    return HttpResponse("ok")


async def async_view_with_loaders(request):
    resp = await sync_to_async(view_with_loaders)(request)
    return resp
