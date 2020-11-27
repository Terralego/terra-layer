from django.apps import AppConfig
from terra_accounts.permissions_mixins import PermissionRegistrationMixin


class TerraLayerConfig(PermissionRegistrationMixin, AppConfig):
    name = "terra_layer"

    permissions = (
        ("DataLayer", "can_manage_layers", "Can manage layers"),
        ("DataSource", "can_manage_sources", "Can manage sources"),
    )
