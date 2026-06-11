import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


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

    # State transition validation mapping
    VALID_TRANSITIONS = {
        Status.REPORTED: [Status.ASSIGNED, Status.CLOSED],
        Status.ASSIGNED: [Status.IN_PROGRESS, Status.REPORTED],
        Status.IN_PROGRESS: [Status.RESOLVED, Status.ASSIGNED],
        Status.RESOLVED: [Status.CLOSED, Status.IN_PROGRESS],
        Status.CLOSED: [Status.IN_PROGRESS]
    }

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        if self.pk:
            # Fetch current status in the database to prevent direct modifications bypassing state machines
            old_instance = Incident.objects.filter(pk=self.pk).only('status').first()
            if old_instance and old_instance.status != self.status:
                valid_next = self.VALID_TRANSITIONS.get(old_instance.status, [])
                if self.status not in valid_next:
                    raise ValidationError(
                        f"Invalid status transition from {old_instance.status} to {self.status}."
                    )

    def save(self, *args, **kwargs):
        # We run clean validations before write
        self.full_clean()
        
        is_new = self._state.adding
        old_status = None
        old_assigned_to = None
        
        if not is_new:
            old_instance = Incident.objects.filter(pk=self.pk).only('status', 'assigned_to').first()
            if old_instance:
                old_status = old_instance.status
                old_assigned_to = old_instance.assigned_to

        # workflow auto-transition status based on assignment context:
        # 1. If assigned_to is set and the status is still REPORTED, transition to ASSIGNED
        if self.assigned_to and not old_assigned_to and self.status == self.Status.REPORTED:
            self.status = self.Status.ASSIGNED
        # 2. If assigned_to is removed/unassigned and status is ASSIGNED, revert back to REPORTED
        elif not self.assigned_to and old_assigned_to and self.status == self.Status.ASSIGNED:
            self.status = self.Status.REPORTED
        
        super().save(*args, **kwargs)
        
        # Track status change history
        if is_new or old_status != self.status:
            changed_by = getattr(self, '_changed_by', None)
            if not changed_by:
                changed_by = self.reported_by if is_new else (self.assigned_to or old_assigned_to)
                
            remarks = getattr(self, '_remarks', '')
            if not remarks:
                remarks = "Incident initially logged." if is_new else f"Status updated to {self.get_status_display()}."
                
            IncidentStatusHistory.objects.create(
                incident=self,
                old_status=old_status,
                new_status=self.status,
                changed_by=changed_by,
                remarks=remarks
            )

        # Track assignment change history
        if is_new or old_assigned_to != self.assigned_to:
            if self.assigned_to or old_assigned_to:
                changed_by = getattr(self, '_changed_by', None)
                remarks = getattr(self, '_remarks', '')
                if not remarks:
                    if not self.assigned_to:
                        remarks = f"Incident unassigned (previously assigned to {old_assigned_to.username})."
                    else:
                        remarks = f"Incident assigned to {self.assigned_to.username}."
                
                IncidentAssignmentHistory.objects.create(
                    incident=self,
                    assigned_by=changed_by,
                    assigned_to=self.assigned_to,
                    remarks=remarks
                )

    def __str__(self):
        return f"{self.title} ({self.category} - {self.status})"


class IncidentStatusHistory(models.Model):
    incident = models.ForeignKey(
        Incident,
        on_delete=models.CASCADE,
        related_name='status_history',
        help_text="The incident whose status was modified."
    )
    old_status = models.CharField(
        max_length=20,
        choices=Incident.Status.choices,
        null=True,
        blank=True,
        help_text="The status prior to this update."
    )
    new_status = models.CharField(
        max_length=20,
        choices=Incident.Status.choices,
        help_text="The status resulting from this update."
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The user who performed the status transition."
    )
    remarks = models.TextField(
        blank=True,
        help_text="Optional comments/reasons detailing the change."
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp of when the transition occurred."
    )

    class Meta:
        ordering = ['timestamp']
        verbose_name_plural = "Incident status histories"

    def __str__(self):
        return f"{self.incident.title}: {self.old_status} -> {self.new_status} at {self.timestamp}"


class IncidentAssignmentHistory(models.Model):
    incident = models.ForeignKey(
        Incident,
        on_delete=models.CASCADE,
        related_name='assignment_history',
        help_text="The incident that was assigned."
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='assignments_made',
        null=True,
        blank=True,
        help_text="The Operator or Admin who assigned the incident."
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='assignments_received',
        null=True,
        blank=True,
        help_text="The Operator assigned to handle the incident."
    )
    remarks = models.TextField(
        blank=True,
        help_text="Optional comments/reasons detailing the assignment change."
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp of when the assignment occurred."
    )

    class Meta:
        ordering = ['timestamp']
        verbose_name_plural = "Incident assignment histories"

    def __str__(self):
        assigner = self.assigned_by.username if self.assigned_by else "System"
        assignee = self.assigned_to.username if self.assigned_to else "Unassigned"
        return f"{self.incident.title} assigned to {assignee} by {assigner} at {self.timestamp}"
