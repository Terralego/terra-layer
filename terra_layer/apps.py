from django.apps import AppConfig
from terra_accounts.permissions_mixins import PermissionRegistrationMixin


class TerraLayerConfig(PermissionRegistrationMixin, AppConfig):
    name = "terra_layer"

    permissions = (
        ("can_manage_layers", "DataLayer: Can manage layers"),
        ("can_manage_sources", "DataSource: Can manage sources"),
    )
