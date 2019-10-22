from django.urls import path
from rest_framework import routers

from .views import LayerViewset, LayerView, SceneViewset

app_name = "terralayer"

router = routers.SimpleRouter()

router.register(r"scene", SceneViewset, base_name="scene")
router.register(r"", LayerViewset, base_name="layer")

urlpatterns = [path(r"view/<str:slug>/", LayerView.as_view(), name="layerview")]

urlpatterns += router.urls
