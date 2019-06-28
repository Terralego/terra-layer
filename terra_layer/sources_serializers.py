import inspect
import sys

from rest_framework import serializers
from django_geosource.models import Source, WMTSSource

DEFAULT_SOURCE_NAME = 'terra'


class SourceSerializer(serializers.BaseSerializer):
    @classmethod
    def get_object_serializer(cls, obj):
        clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
        for _, serializer in clsmembers:
            if serializer.__module__ == __name__ and serializer.Meta.model is obj.source.__class__:
                return serializer(obj)

        return cls(obj)

    def to_representation(self, obj):
        return {
            **obj.style,
            'id': obj.layer_identifier,
            'source': DEFAULT_SOURCE_NAME,
            'source-layer': obj.source.slug,
        }

    class Meta:
        model = Source

class WMTSSourceSerializer(SourceSerializer):
    def to_representation(self, obj):
        return {
            **obj.style,
            'id': obj.layer_identifier,
            'type': 'raster',
            'minzoom': obj.source.minzoom or 0,
            'maxzoom': obj.source.maxzoom or 26,
            'source': {
                'type': 'raster',
                'tileSize': obj.source.tile_size,
                'tiles': [
                    obj.source.url,
                ],
            },
        }

    class Meta:
        model = WMTSSource
