import json
import re
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from domovoy.security.hashcash import (
    HASHCASH_DIFFICULTY,
    get_hashcash_config,
    make_header,
)

from domovoy.testing import ApiClient, make_user

User = get_user_model()


class RegisterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(username="taken", email="taken@example.com")

    def register(self, username, email):
        nonce = get_hashcash_config()["nonces"][0]
        return self.client.post(
            "/api/users/v1/new",
            data=json.dumps(
                {
                    "username": username,
                    "email": email,
                    "name_short": "New",
                    "name_full": "New User",
                    "password": "correct-horse-battery",
                }
            ),
            content_type="application/json",
            HTTP_X_HASHCASH=make_header(email, HASHCASH_DIFFICULTY, nonce),
        )

    def test_duplicate_username_is_rejected(self):
        response = self.register("taken", "new@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Username already in use"})

    def test_duplicate_email_is_rejected(self):
        response = self.register("newname", "taken@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Email already in use"})
        self.assertFalse(User.objects.filter(username="newname").exists())


SEND_EMAIL = "domovoy.apps.dmv_user.models.send_formatted_email"


def code_from(send_email):
    """The login code in the last email sent through the mocked sender."""
    message = send_email.call_args.kwargs["message"]
    return re.search(r"auth_link/[^/\s]+/([0-9a-f-]{36})", message).group(1)


class EmailCodeTests(TestCase):
    def setUp(self):
        self.user = make_user("alice", email_verified=False)
        patcher = mock.patch(SEND_EMAIL)
        self.send_email = patcher.start()
        self.addCleanup(patcher.stop)

    def send(self):
        sent = self.user.send_email_code()
        self.user.refresh_from_db()
        return sent

    def test_a_code_logs_in_once_and_verifies_the_email(self):
        self.assertTrue(self.send())
        code = code_from(self.send_email)
        self.assertTrue(self.user.verify_email_code(code))
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)
        self.assertIsNone(self.user.email_link_hash)
        self.assertFalse(self.user.verify_email_code(code))

    def test_only_a_hash_of_the_code_is_stored(self):
        self.send()
        self.assertNotIn(code_from(self.send_email), self.user.email_link_hash)

    def test_wrong_code_is_rejected(self):
        self.send()
        self.assertFalse(self.user.verify_email_code("00000000-0000-0000-0000-000000000000"))
        self.assertFalse(User.objects.get(pk=self.user.pk).email_verified)

    def test_no_code_sent(self):
        self.assertFalse(self.user.verify_email_code("anything"))

    def test_code_expires_after_30_minutes(self):
        self.send()
        code = code_from(self.send_email)
        self.user.email_link_sent -= timedelta(minutes=31)
        self.user.save()
        self.assertFalse(self.user.verify_email_code(code))

    def test_resend_waits_a_minute_and_replaces_the_code(self):
        self.send()
        first_code = code_from(self.send_email)
        self.assertFalse(self.send())
        self.assertEqual(self.send_email.call_count, 1)

        self.user.email_link_sent -= timedelta(minutes=2)
        self.user.save()
        self.assertTrue(self.send())
        self.assertEqual(self.send_email.call_count, 2)
        self.assertFalse(self.user.verify_email_code(first_code))
        self.assertTrue(self.user.verify_email_code(code_from(self.send_email)))

    def test_email_code_endpoint(self):
        def request(email, subject):
            nonce = get_hashcash_config()["nonces"][0]
            return Client().post(
                f"/api/users/v1/email_code?email={email}",
                HTTP_X_HASHCASH=make_header(subject, HASHCASH_DIFFICULTY, nonce),
            )

        self.assertEqual(request("alice@example.com", "someone@example.com").status_code, 401)
        self.assertEqual(request("nobody@example.com", "nobody@example.com").status_code, 401)
        self.assertEqual(self.send_email.call_count, 0)
        self.assertEqual(request("alice@example.com", "alice@example.com").status_code, 200)
        self.assertEqual(self.send_email.call_args.kwargs["recipient"], "alice@example.com")


class SessionApiTests(TestCase):
    URL = "/api/users/v1/session"

    @classmethod
    def setUpTestData(cls):
        cls.alice = make_user("alice")
        cls.alice.set_password("correct-horse-battery")
        cls.alice.save()

    def log_in(self, email="alice@example.com", **factor):
        factor = factor or {"factor_type": "password", "password": "correct-horse-battery"}
        body = {"email": email, "factors": [factor] if factor != {"none": True} else []}
        return Client().post(self.URL, data=json.dumps(body), content_type="application/json")

    def active_session(self, key):
        return Client().get(self.URL, HTTP_X_SESSION_KEY=key)

    def test_password_login_returns_a_working_session_key(self):
        response = self.log_in()
        self.assertEqual(response.status_code, 200)
        key = response.json()
        self.assertEqual(response["x-session-key"], key)
        me = self.active_session(key)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["username"], "alice@example.com")

    def test_rejected_logins(self):
        cases = {
            "wrong password": self.log_in(factor_type="password", password="nope-nope-nope"),
            "unknown email": self.log_in("nobody@example.com"),
            "no factors": self.log_in(none=True),
        }
        self.assertEqual({k: r.status_code for k, r in cases.items()}, dict.fromkeys(cases, 401))

    def test_unverified_user_cannot_log_in_with_a_password(self):
        bob = make_user("bob", email_verified=False)
        bob.set_password("correct-horse-battery")
        bob.save()
        self.assertEqual(self.log_in("bob@example.com").status_code, 401)

    def test_email_code_login_verifies_a_new_user(self):
        bob = make_user("bob", email_verified=False)
        with mock.patch(SEND_EMAIL) as send_email:
            bob.send_email_code()
        response = self.log_in(
            "bob@example.com", factor_type="email_code", email_code=code_from(send_email)
        )
        self.assertEqual(response.status_code, 200)
        bob.refresh_from_db()
        self.assertTrue(bob.email_verified)

    def test_logout_ends_the_session(self):
        key = self.log_in().json()
        self.assertEqual(
            Client().delete(self.URL, HTTP_X_SESSION_KEY=key).status_code, 200
        )
        self.assertEqual(self.active_session(key).status_code, 401)

    def test_unknown_or_missing_session_key(self):
        self.assertEqual(self.active_session("not-a-session").status_code, 401)
        self.assertEqual(Client().get(self.URL).status_code, 401)

    def test_session_of_a_user_whose_email_is_unverified(self):
        api = ApiClient(self.alice)
        User.objects.filter(pk=self.alice.pk).update(email_verified=False)
        self.assertEqual(api.get(self.URL).status_code, 401)
