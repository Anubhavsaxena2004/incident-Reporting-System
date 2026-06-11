from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema

from .models import Incident
from .serializers import (
    IncidentSerializer,
    IncidentStatusHistorySerializer,
    IncidentAssignmentHistorySerializer
)
from .filters import IncidentFilter
from .permissions import IsIncidentOwnerOrAssignee


class IncidentPagination(PageNumberPagination):
    """
    Production-ready pagination class with dynamic page size overrides.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


@extend_schema(
    summary="Incident Management CRUD",
    description="API viewset supporting full lifecycle operations for incidents. Filters, sorting, search, and pagination are fully enabled."
)
class IncidentViewSet(viewsets.ModelViewSet):
    # Optimize query structure to load foreign key instances concurrently (select_related)
    queryset = Incident.objects.all().select_related('reported_by', 'assigned_to')
    serializer_class = IncidentSerializer
    
    # Configure strict authentication and object-level permissions
    permission_classes = [permissions.IsAuthenticated, IsIncidentOwnerOrAssignee]
    
    # Enable filtering, searching, and sorting capabilities
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = IncidentFilter
    search_fields = ('title', 'description', 'address')
    ordering_fields = ('created_at', 'updated_at', 'priority', 'status')
    ordering = ('-created_at',)
    pagination_class = IncidentPagination

    def perform_create(self, serializer):
        # Automatically assign reported_by user as current authenticated user
        serializer.save(reported_by=self.request.user)

    def get_queryset(self):
        user = self.request.user
        
        # Base query optimization applying select_related on related User models
        qs = self.queryset
        
        # Superusers, Admins get access to all incidents
        if user.is_superuser or user.role == user.Role.ADMIN:
            return qs
            
        # Operators can only view incidents assigned to them
        if user.role == user.Role.OPERATOR:
            return qs.filter(assigned_to=user)
            
        # Standard Citizens can only view incidents they personally reported
        return qs.filter(reported_by=user)

    @extend_schema(
        summary="Delete Incident Record",
        description="Removes an incident from the database. Strictly restricted to system Administrators."
    )
    def destroy(self, request, *args, **kwargs):
        user = request.user
        
        # Enforce that only system Admins can hard delete incidents for audit/accountability reasons
        if user.role != user.Role.ADMIN and not user.is_superuser:
            return Response(
                {"detail": "Permission denied. Only Administrators can delete incident records."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="View Incident Status Timeline",
        description="Retrieves the chronologically sorted history logs detailing status transitions (old status -> new status) and remarks.",
        responses={200: IncidentStatusHistorySerializer(many=True)}
    )
    @action(detail=True, methods=['get'], url_path='timeline')
    def timeline(self, request, pk=None):
        """
        Retrieves the complete state transition history for a specific incident.
        """
        incident = self.get_object()
        history = incident.status_history.all().order_by('timestamp')
        serializer = IncidentStatusHistorySerializer(history, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="View Incident Assignment History",
        description="Retrieves the complete history logs detailing who assigned the incident and to whom it was delegated.",
        responses={200: IncidentAssignmentHistorySerializer(many=True)}
    )
    @action(detail=True, methods=['get'], url_path='assignments')
    def assignments(self, request, pk=None):
        """
        Retrieves the complete assignment history logs for a specific incident.
        """
        incident = self.get_object()
        history = incident.assignment_history.all().order_by('timestamp')
        serializer = IncidentAssignmentHistorySerializer(history, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
