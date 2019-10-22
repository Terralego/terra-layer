from rest_framework import permissions


class LayerPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm("terra_layer.can_manage_layers")


class ScenePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.has_perm("terra_layer.can_manage_layers")
