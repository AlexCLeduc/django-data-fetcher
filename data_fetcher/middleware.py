#!/usr/bin/env python
# -*- coding: utf8 -*-
from __future__ import (
    absolute_import,
    division,
    generators,
    nested_scopes,
    print_function,
    unicode_literals,
    with_statement,
)

import threading

from django.http import HttpRequest


class GlobalRequestStorage(object):
    storage = threading.local()

    def get(self):
        if hasattr(self.storage, "request"):
            return self.storage.request
        else:
            return None

    def set(self, request):
        self.storage.request = request

    def recover(self, request=None):
        if hasattr(self.storage, "request"):
            del self.storage.request
        if request:
            self.storage.request = request


class GlobalRequest(object):

    def __init__(self, request=None):
        self.global_request_storage = GlobalRequestStorage()
        self.new_request = request or HttpRequest()
        self.old_request = self.global_request_storage.get()

    def __enter__(self):
        self.global_request_storage.set(self.new_request)
        return self.global_request_storage.get()

    def __exit__(self, *args, **kwargs):
        self.global_request_storage.recover(request=self.old_request)


class GlobalRequestMiddleware(object):

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with GlobalRequest(request=request):
            return self.get_response(request)


def get_request():
    return GlobalRequestStorage().get()
