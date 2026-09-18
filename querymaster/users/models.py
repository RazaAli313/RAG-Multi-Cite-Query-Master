from typing import ClassVar

from django.contrib.auth.models import AbstractUser

from .fields import EmailField
from .managers import UserManager


class User(AbstractUser):
    email = EmailField(unique=True)

    username = None
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects = UserManager()

    def __str__(self):
        return self.email
