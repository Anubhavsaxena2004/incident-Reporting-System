from django.db import models
from django.conf import settings


class Incident(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        REPORTED = 'REPORTED', 'Reported'
        UNDER_INVESTIGATION = 'UNDER_INVESTIGATION', 'Under Investigation'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'

    title = models.CharField(
        max_length=150, 
        help_text="Brief summary of the emergency event."
    )
    description = models.TextField(
        help_text="Detailed description of the incident circumstances."
    )
    location = models.CharField(
        max_length=255, 
        help_text="Physical address or geographical reference of the incident."
    )
    
    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.REPORTED,
        help_text="Current state in the incident lifecycle."
    )
    priority = models.CharField(
        max_length=15,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        help_text="Urgency level of the incident response."
    )
    
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reported_incidents',
        help_text="The system user who originally logged the incident."
    )
    assigned_responder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='assigned_incidents',
        null=True,
        blank=True,
        help_text="The field responder assigned to resolve this incident."
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.status} ({self.priority})"
