from django.contrib import admin
from mapbox_baselayer.admin import MapBaseLayerAdmin
from mapbox_baselayer.models import MapBaseLayer

admin.site.register(MapBaseLayer, MapBaseLayerAdmin)
