from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """
    Allows access only to Admin users.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (request.user.role == 'ADMIN' or request.user.is_superuser)
        )


class IsOperator(permissions.BasePermission):
    """
    Allows access to Operators or Admin users.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (request.user.role in ['OPERATOR', 'ADMIN'] or request.user.is_superuser)
        )


class IsCitizen(permissions.BasePermission):
    """
    Allows access only to Citizen users.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'CITIZEN'
        )
