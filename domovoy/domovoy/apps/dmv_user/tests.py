import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from domovoy.security.hashcash import (
    HASHCASH_DIFFICULTY,
    get_hashcash_config,
    make_header,
)

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
