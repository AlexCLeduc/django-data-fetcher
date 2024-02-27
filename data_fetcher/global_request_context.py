import contextvars

from django.http import HttpRequest

storage = contextvars.ContextVar("request", default=None)


class GlobalRequest:
    """
    get_request() will return the same object
    within this ctx-manager's block

    """

    def __init__(self, request=None):
        self.new_request = request or HttpRequest()
        self.old_request = storage.get()

    def __enter__(self):
        storage.set(self.new_request)
        return storage.get()

    def __exit__(self, *args, **kwargs):
        storage.set(self.old_request)


def get_request():
    return storage.get()
