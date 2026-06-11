from django.contrib import admin
from .models import Incident, IncidentStatusHistory, IncidentAssignmentHistory


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'priority', 'reported_by', 'assigned_to', 'created_at')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('title', 'description', 'location')


@admin.register(IncidentStatusHistory)
class IncidentStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('incident', 'old_status', 'new_status', 'changed_by', 'timestamp')
    list_filter = ('old_status', 'new_status', 'timestamp')
    search_fields = ('incident__title', 'remarks')


@admin.register(IncidentAssignmentHistory)
class IncidentAssignmentHistoryAdmin(admin.ModelAdmin):
    list_display = ('incident', 'assigned_by', 'assigned_to', 'timestamp')
    list_filter = ('assigned_by', 'assigned_to', 'timestamp')
    search_fields = ('incident__title', 'remarks')
