from rest_framework.permissions import BasePermission


class IsStaffOrReadOnly(BasePermission):
    """
    Allow any access to retrieve (list/detail) views.
    Only allow write access (create/update/delete) to staff users.
    """

    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user and request.user.is_staff