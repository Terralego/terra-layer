from django.http import HttpResponseNotFound
from django.urls import path, include
from rest_framework import routers

from ..views import (
    GeostoreLayerViewSet,
    GeostoreLayerGroupViewsSet,
    GeostoreFeatureViewSet,
)


router = routers.SimpleRouter()

router.register(r"layer", GeostoreLayerViewSet, base_name="layer")
router.register(r"group", GeostoreLayerGroupViewsSet, base_name="group"),

router.register(
    r"layer/(?P<layer>[\d\w\-_]+)/feature", GeostoreFeatureViewSet, base_name="feature"
)

urlpatterns = [path("", include(router.urls))]
