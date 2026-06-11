from rest_framework import viewsets, permissions
from .models import Incident
from .serializers import IncidentSerializer


class IncidentViewSet(viewsets.ModelViewSet):
    queryset = Incident.objects.all().select_related('reporter', 'assigned_responder')
    serializer_class = IncidentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Inject the current authenticated user as the reporter
        serializer.save(reporter=self.request.user)

    def get_queryset(self):
        user = self.request.user
        
        # Superusers, Admins, and Operators get access to the full incident list
        if user.is_superuser or user.role in [user.Role.ADMIN, user.Role.OPERATOR]:
            return self.queryset
            
        # Standard Citizens only get access to incidents they filed
        return self.queryset.filter(reporter=user)
