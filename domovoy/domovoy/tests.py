import re

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

RUN_APP_HOST = "domovoy-dev-abc123-nw.a.run.app"
WEB_APP_ORIGIN = "https://domovoy-dev.web.app"

# The settings docs/DEPLOY_GCP.md sets on Cloud Run.
GCP_SETTINGS = dict(
    ALLOWED_HOSTS=[RUN_APP_HOST],
    CSRF_TRUSTED_ORIGINS=[WEB_APP_ORIGIN],
    SESSION_COOKIE_NAME="__session",
    CSRF_USE_SESSIONS=True,
    MESSAGE_STORAGE="django.contrib.messages.storage.session.SessionStorage",
)


class FirebaseProxyClient(Client):
    """Behaves like a browser on the web.app site behind a Firebase rewrite.

    Firebase Hosting forwards only the "__session" cookie to Cloud Run, sends
    the run.app hostname as Host, and the browser sends the web.app Origin.
    """

    def request(self, **request):
        for name in list(self.cookies):
            if name != "__session":
                del self.cookies[name]
        request.setdefault("HTTP_HOST", RUN_APP_HOST)
        request.setdefault("HTTP_X_FORWARDED_PROTO", "https")
        if request["REQUEST_METHOD"] == "POST":
            request.setdefault("HTTP_ORIGIN", WEB_APP_ORIGIN)
        return super().request(**request)


# The manifest storage needs collectstatic output, which tests don't build.
@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
)
class AdminBehindFirebaseTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="pw-for-tests"
        )

    def _login(self):
        client = FirebaseProxyClient(enforce_csrf_checks=True)
        page = client.get("/krimba/login/")
        self.assertEqual(page.status_code, 200)
        token = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"', page.content.decode()
        ).group(1)
        response = client.post(
            "/krimba/login/?next=/krimba/",
            {
                "username": "admin",
                "password": "pw-for-tests",
                "csrfmiddlewaretoken": token,
            },
        )
        return client, response

    @override_settings(**GCP_SETTINGS)
    def test_admin_login_works_with_gcp_settings(self):
        client, response = self._login()
        self.assertEqual(response.status_code, 302, response.content[:500])
        self.assertEqual(response["Location"], "/krimba/")
        self.assertEqual(client.get("/krimba/").status_code, 200)

    @override_settings(
        ALLOWED_HOSTS=GCP_SETTINGS["ALLOWED_HOSTS"],
        CSRF_TRUSTED_ORIGINS=GCP_SETTINGS["CSRF_TRUSTED_ORIGINS"],
    )
    def test_admin_login_fails_with_default_cookie_settings(self):
        _, response = self._login()
        self.assertEqual(response.status_code, 403)


class CacheControlTests(TestCase):
    def test_api_responses_are_not_cacheable(self):
        response = self.client.get("/api/openapi.json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("private", response["Cache-Control"])
