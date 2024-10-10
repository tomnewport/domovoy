from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class DmvUser(AbstractUser):
    username = models.EmailField(unique=True)
    email = models.EmailField(blank=True, null=True)
    first_name = None
    last_name = None

    name_short = models.CharField(blank=True, null=True, max_length=16)
    name_full = models.CharField(blank=True, null=True, max_length=128)

    email_verified = models.BooleanField(default=False)

    email_link_hash = models.CharField(max_length=256)
    email_link_expires = models.DateTimeField(blank=True, null=True)

    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

