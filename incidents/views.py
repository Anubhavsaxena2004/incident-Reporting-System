from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Incident
from .serializers import (
    IncidentSerializer,
    IncidentStatusHistorySerializer,
    IncidentAssignmentHistorySerializer
)


class IncidentViewSet(viewsets.ModelViewSet):
    queryset = Incident.objects.all().select_related('reported_by', 'assigned_to')
    serializer_class = IncidentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Automatically assign reported_by user as current authenticated user
        serializer.save(reported_by=self.request.user)

    def get_queryset(self):
        user = self.request.user
        
        # Superusers, Admins, and Operators can view all incidents in the system
        if user.is_superuser or user.role in [user.Role.ADMIN, user.Role.OPERATOR]:
            return self.queryset
            
        # Standard Citizens can only view incidents they personally reported
        return self.queryset.filter(reported_by=user)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        
        # Enforce that only system Admins can hard delete incidents for audit/accountability reasons
        if user.role != user.Role.ADMIN and not user.is_superuser:
            return Response(
                {"detail": "Permission denied. Only Administrators can delete incident records."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'], url_path='timeline')
    def timeline(self, request, pk=None):
        """
        Retrieves the complete state transition history for a specific incident.
        """
        incident = self.get_object()
        history = incident.status_history.all().order_by('timestamp')
        serializer = IncidentStatusHistorySerializer(history, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='assignments')
    def assignments(self, request, pk=None):
        """
        Retrieves the complete assignment history logs for a specific incident.
        """
        incident = self.get_object()
        history = incident.assignment_history.all().order_by('timestamp')
        serializer = IncidentAssignmentHistorySerializer(history, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
