from django.urls import path, include
from rest_framework import routers

from ..views import (
    GeostoreLayerViewSet,
    GeostoreLayerGroupViewsSet,
    GeostoreFeatureViewSet,
)


router = routers.DefaultRouter()

router.register(r"layer", GeostoreLayerViewSet, basename="layer")
router.register(r"group", GeostoreLayerGroupViewsSet, basename="group"),

router.register(
    r"layer/(?P<layer>[\d\w\-_]+)/feature", GeostoreFeatureViewSet, basename="feature"
)

urlpatterns = [path("", include(router.urls))]
