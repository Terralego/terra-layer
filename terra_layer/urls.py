from django.urls import path
from rest_framework import routers

from .views import LayerViewset, LayerView, SceneViewset

app_name = "terralayer"

router = routers.SimpleRouter()

router.register(r'layer', LayerViewset, base_name='layer')
router.register(r'scene', SceneViewset, base_name='scene')

scene_list = SceneViewset.as_view({
    'get': 'list',
    'post': 'create'
})

scene_detail = SceneViewset.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    path(r'view/', LayerView.as_view(), name='layerview'),
    path(r'view/<str:slug>/', LayerView.as_view(), name='layerview'),
    path(r'scene/', scene_list, name='scene-list'),
    path(r'scene/<str:slug>/', scene_detail, name='scene-detail'),
]

urlpatterns += router.urls
