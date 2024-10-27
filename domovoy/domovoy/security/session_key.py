from django.contrib.auth import get_user_model
from ninja.errors import HttpError
from ninja.security import APIKeyHeader

from importlib import import_module

from django.conf import settings

User = get_user_model()


class SessionHeader(APIKeyHeader):
    # Specify the header name to look for
    param_name = "x-session-key"

    def __init__(self):
        super().__init__()
        engine = import_module(settings.SESSION_ENGINE)
        self.SessionStore = engine.SessionStore

    def authenticate(self, request, key):
        # The key is the value from the 'x-session-key' header
        session_key = key

        # Load the session using the provided session key
        session = self.SessionStore(session_key=session_key)

        request.session = session

        # Check if the session exists or is valid
        if not session.exists(session_key):
            raise HttpError(401, "Invalid session key")

        session_data = session.load()
        user_id = session_data.get("_auth_user_id")

        if not user_id:
            raise HttpError(401, "Unauthorized")

        try:
            user = User.objects.get(id=user_id, email_verified=True)
        except User.DoesNotExist:
            raise HttpError(401, "Unauthorized")

        return user
