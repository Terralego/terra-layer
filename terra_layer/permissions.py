from rest_framework import permissions


class LayerPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm("terra_layer.can_manage_layers")
