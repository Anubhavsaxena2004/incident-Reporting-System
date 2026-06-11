from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class IsIncidentOwnerOrAssignee(permissions.BasePermission):
    """
    Object-level permission checking role-based ownership:
    - Admin: Full access.
    - Operator: Can only view and edit incidents assigned to them.
    - Citizen: Can only view and edit incidents they reported.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # 1. Admins/Superusers get unrestricted access
        if user.is_superuser or user.role == User.Role.ADMIN:
            return True
            
        # 2. Operators can only access incidents assigned to them
        if user.role == User.Role.OPERATOR:
            return obj.assigned_to == user
            
        # 3. Citizens can only access incidents they reported
        if user.role == User.Role.CITIZEN:
            return obj.reported_by == user

        return False
