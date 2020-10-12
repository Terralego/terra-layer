from django.urls import include, path
from rest_framework import routers

from .geostore import urlpatterns as geostore_patterns
from .geosource import router as geosource_router
from ..views import LayerViewset, LayerView, SceneViewset

router = routers.SimpleRouter()

router.register(r"geolayer/scene", SceneViewset, basename="scene")
router.register(r"geolayer", LayerViewset, basename="layer")

# Extras viewsets

urlpatterns = [
    path(r"geolayer/view/<str:slug>/", LayerView.as_view(), name="layerview"),
    # Extra urls from third part modules
    path("", include("terra_accounts.urls")),
    path("", include("terra_settings.urls")),
    path("", include("mapbox_baselayer.urls")),
    path("geostore/", include(geostore_patterns)),
    path(
        "geosource/",
        include((geosource_router.urls, "geosource"), namespace="geosource"),
    ),
]

urlpatterns += router.urls
