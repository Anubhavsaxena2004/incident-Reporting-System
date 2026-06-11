from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        DISPATCHER = 'DISPATCHER', 'Dispatcher'
        RESPONDER = 'RESPONDER', 'Responder'
        REPORTER = 'REPORTER', 'Reporter'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.REPORTER,
        help_text="Role determining user authorization levels."
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="Contact number for notifications or field coordination."
    )

    def __str__(self):
        return f"{self.username} ({self.role})"
