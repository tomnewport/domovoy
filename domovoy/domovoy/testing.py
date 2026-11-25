"""Helpers shared by the test suites, and the project's test runner."""

import warnings

from django.contrib.auth import get_user_model
from django.test import Client
from django.test.runner import DiscoverRunner
from pydantic.warnings import PydanticDeprecatedSince20


class TestRunner(DiscoverRunner):
    """Django's runner, but a deprecated Pydantic v1 API (`parse_obj`,
    `.dict()`, ...) used while the tests run fails the test that hits it (#14).

    Pydantic attributes these warnings to its own modules, not the caller, so
    the filter can't be limited to our code. Instead the API is imported first:
    django-ninja still uses class-based `Config` internally and warns about it
    once, at import. Our own models' class-based `Config` is checked by
    PydanticConfigTests.
    """

    def run_tests(self, *args, **kwargs):
        import domovoy.urls  # noqa: F401 -- see above

        with warnings.catch_warnings():
            warnings.filterwarnings("error", category=PydanticDeprecatedSince20)
            return super().run_tests(*args, **kwargs)


def make_user(name, **kwargs):
    """A user called `name`, with `name@example.com` as username and email.

    Verified unless `email_verified=False` is passed.
    """
    kwargs.setdefault("email_verified", True)
    return get_user_model().objects.create_user(
        username=f"{name}@example.com",
        email=f"{name}@example.com",
        name_short=name.title(),
        name_full=name.title(),
        **kwargs,
    )


class ApiClient(Client):
    """Calls the API as `user`, sending the x-session-key header like the SPA."""

    def __init__(self, user, **defaults):
        login = Client()
        login.force_login(user)
        super().__init__(HTTP_X_SESSION_KEY=login.session.session_key, **defaults)

    def post_json(self, path, data=None):
        return self.post(path, data=data or {}, content_type="application/json")

    def patch_json(self, path, data=None):
        return self.patch(path, data=data or {}, content_type="application/json")
