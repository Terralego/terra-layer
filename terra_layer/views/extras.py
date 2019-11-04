from django_geosource.views import SourceModelViewset
from geostore.views import FeatureViewSet, LayerViewSet, LayerGroupViewsSet


class GeoSourceModelViewset(SourceModelViewset):
    pass


class GeostoreLayerViewSet(LayerViewSet):
    pass


class GeostoreFeatureViewSet(FeatureViewSet):
    pass


class GeostoreLayerGroupViewsSet(LayerGroupViewsSet):
    pass
