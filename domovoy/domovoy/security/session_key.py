from django.contrib.auth import HASH_SESSION_KEY, get_user_model
from django.utils.crypto import constant_time_compare
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

        self._resign_if_signed_with_old_key(session, session_data, user)

        return user

    @staticmethod
    def _resign_if_signed_with_old_key(session, session_data, user):
        """Move a session made under a previous SECRET_KEY to the current one.

        Its auth hash then only matches a SECRET_KEY_FALLBACKS key. Django's
        get_user() (behind request.user) would accept it but cycle the session
        key, and the SPA, which only learns its key at login, would be logged
        out on its next request. Instead, update the hash and save the session
        under the same key, which also re-signs its data with the current key.
        """
        session_hash = session_data.get(HASH_SESSION_KEY)
        current_hash = user.get_session_auth_hash()
        if not session_hash or constant_time_compare(session_hash, current_hash):
            return
        if any(
            constant_time_compare(session_hash, fallback_hash)
            for fallback_hash in user.get_session_auth_fallback_hash()
        ):
            session[HASH_SESSION_KEY] = current_hash
            session.save()
