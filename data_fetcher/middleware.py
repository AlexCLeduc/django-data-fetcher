from .global_request_context import GlobalRequest


class GlobalRequestMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with GlobalRequest(request=request):
            return self.get_response(request)
