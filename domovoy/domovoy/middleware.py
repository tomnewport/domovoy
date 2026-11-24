from asgiref.sync import iscoroutinefunction
from django.utils.cache import add_never_cache_headers
from django.utils.decorators import sync_and_async_middleware


def _never_cache_unless_set(response):
    if not response.has_header("Cache-Control"):
        add_never_cache_headers(response)
    return response


@sync_and_async_middleware
def never_cache_by_default(get_response):
    """Mark dynamic responses uncacheable unless a view chose otherwise.

    API responses depend on the x-session-key header, which a shared cache in
    front of the app (e.g. Firebase Hosting's CDN) does not key on. An explicit
    no-store keeps one user's response from being served to another.
    """
    if iscoroutinefunction(get_response):

        async def middleware(request):
            return _never_cache_unless_set(await get_response(request))

    else:

        def middleware(request):
            return _never_cache_unless_set(get_response(request))

    return middleware
