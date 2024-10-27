import uuid
from base64 import urlsafe_b64encode
from datetime import timedelta

from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.conf import settings

from domovoy.utils.email import send_formatted_email

EMAIL_LINK_EXPIRY = timedelta(minutes=30)
EMAIL_LINK_BACKOFF = timedelta(minutes=1)


class DmvUser(AbstractUser):
    name_short = models.CharField(blank=True, null=True, max_length=16)
    name_full = models.CharField(blank=True, null=True, max_length=128)

    email_verified = models.BooleanField(default=False)

    email_link_hash = models.CharField(max_length=256, blank=True, null=True)
    email_link_sent = models.DateTimeField(blank=True, null=True)

    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.name_full} ({self.email})"

    def send_email_code(self):
        user_b64 = urlsafe_b64encode(self.email.encode()).decode().strip("=")
        if (
            self.email_link_sent
            and self.email_link_sent > timezone.now() - EMAIL_LINK_BACKOFF
        ):
            return False

        self.email_link_sent = timezone.now()
        email_code = str(uuid.uuid4())
        self.email_link_hash = make_password(email_code)
        send_formatted_email(
            subject="Your login link",
            recipient=self.email,
            message=f"""
Hi {self.name_short},

Please use this link to log in to the Domovoy app.

{settings.FRONTEND_ROOT}auth_link/{user_b64}/{email_code}
""",
        )
        self.save()
        return True

    def verify_email_code(self, code: str):
        if self.email_link_hash is None:
            return False
        if self.email_link_sent < (timezone.now() - EMAIL_LINK_EXPIRY):
            return False
        if not check_password(code, self.email_link_hash):
            return False

        self.email_link_sent = None
        self.email_link_hash = None
        self.email_verified = True
        self.save()

        return True
