import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Incident(models.Model):
    class Category(models.TextChoices):
        FIRE = 'FIRE', 'Fire'
        ACCIDENT = 'ACCIDENT', 'Accident'
        MEDICAL = 'MEDICAL', 'Medical'
        CRIME = 'CRIME', 'Crime'
        NATURAL_DISASTER = 'NATURAL_DISASTER', 'Natural Disaster'
        OTHER = 'OTHER', 'Other'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    class Status(models.TextChoices):
        REPORTED = 'REPORTED', 'Reported'
        ASSIGNED = 'ASSIGNED', 'Assigned'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'

    incident_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the incident."
    )
    title = models.CharField(
        max_length=150,
        help_text="Title summarizing the incident."
    )
    description = models.TextField(
        help_text="Detailed description of the incident."
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
        help_text="Categorization of the incident event."
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)],
        help_text="WGS 84 latitude coordinates."
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)],
        help_text="WGS 84 longitude coordinates."
    )
    address = models.TextField(
        help_text="Physical location details."
    )
    image = models.ImageField(
        upload_to='incidents/',
        null=True,
        blank=True,
        help_text="Attached incident capture."
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REPORTED,
        help_text="Development status of incident lifecycle."
    )
    priority = models.CharField(
        max_length=15,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        help_text="System-assigned urgency level."
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reported_incidents',
        help_text="The Citizen user who logged this incident."
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='assigned_incidents',
        null=True,
        blank=True,
        help_text="The Operator assigned to resolve or dispatch."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.category} - {self.status})"
