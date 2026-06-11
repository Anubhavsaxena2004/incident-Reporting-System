import django_filters
from .models import Incident


class IncidentFilter(django_filters.FilterSet):
    # Date range filters on creation timestamp
    created_at_gte = django_filters.DateTimeFilter(
        field_name='created_at', 
        lookup_expr='gte',
        help_text="Filter incidents created on or after this timestamp (ISO 8601 format)."
    )
    created_at_lte = django_filters.DateTimeFilter(
        field_name='created_at', 
        lookup_expr='lte',
        help_text="Filter incidents created on or before this timestamp (ISO 8601 format)."
    )

    class Meta:
        model = Incident
        fields = {
            'status': ['exact'],
            'priority': ['exact'],
            'category': ['exact'],
            'assigned_to': ['exact'],
            'reported_by': ['exact'],
        }
