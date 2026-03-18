from django.http import HttpResponsePermanentRedirect


class WWWRedirectMiddleware:
    """
    Redirect non-www requests to www.
    Works in both development and production.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().lower()
        
        # Check if the host doesn't start with 'www.' and isn't localhost or IP
        if not host.startswith('www.') and not host.startswith('localhost') and not host.replace('.', '').replace(':', '').isdigit():
            # Build the new URL with www
            new_url = f"{request.scheme}://www.{host}{request.get_full_path()}"
            return HttpResponsePermanentRedirect(new_url)
        
        response = self.get_response(request)
        return response
