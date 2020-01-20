from django.apps import AppConfig
from terra_accounts.permissions_mixins import PermissionRegistrationMixin


class TerraLayerConfig(PermissionRegistrationMixin, AppConfig):
    name = "terra_layer"

    permissions = (
        ("can_manage_layers", "Can manage layers"),
        ("can_manage_sources", "Can manage sources"),
    )
