from rest_framework import routers

from .views import LayerViewset

app_name = 'terralayer'

router = routers.SimpleRouter()

router.register(r'', LayerViewset, base_name='layer')

urlpatterns = router.urls
