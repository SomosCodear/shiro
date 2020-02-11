from rest_framework import permissions


class IsCustomer(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and hasattr(request.user, 'customer')
