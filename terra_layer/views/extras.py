from django_geosource.views import SourceModelViewset
from geostore.views import FeatureViewSet, LayerViewSet, LayerGroupViewsSet

from ..permissions import ReadOnly, SourcePermission


class GeoSourceModelViewset(SourceModelViewset):
    permission_classes = (SourcePermission,)


class GeostoreLayerViewSet(LayerViewSet):
    permission_classes = (ReadOnly,)


class GeostoreFeatureViewSet(FeatureViewSet):
    permission_classes = (ReadOnly,)


class GeostoreLayerGroupViewsSet(LayerGroupViewsSet):
    permission_classes = (ReadOnly,)
