from django.urls import path
from rest_framework import routers

from .views import LayerViewset, LayerViews

app_name = "terralayer"

router = routers.SimpleRouter()

router.register(r"", LayerViewset, base_name="layer")

urlpatterns = [
    path(r"view/", LayerViews.as_view(), name="layerview"),
    path(r"view/<str:slug>/", LayerViews.as_view(), name="layerview"),
]

urlpatterns += router.urls
