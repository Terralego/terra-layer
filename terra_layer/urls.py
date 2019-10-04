from django.urls import path
from rest_framework import routers

from .views import LayerViewset, LayerView, SceneViewset

app_name = "terralayer"

router = routers.SimpleRouter()

router.register(r'layer', LayerViewset, base_name='layer')
router.register(r'scene', SceneViewset, base_name='scene')

urlpatterns = [
    path(r'view/<str:slug>/', LayerView.as_view(), name='layerview'),
]

urlpatterns += router.urls
