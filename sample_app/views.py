from django.http.response import HttpResponse

from .models import Book


def edit_book(request, pk=None):
    book = Book.objects.get(pk=pk)
    if request.POST:
        new_name = request.POST["title"]
        book.title = new_name
        book.save()

    return HttpResponse()
