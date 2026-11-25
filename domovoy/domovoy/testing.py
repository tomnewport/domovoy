"""Helpers shared by the test suites."""

from django.contrib.auth import get_user_model
from django.test import Client


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
