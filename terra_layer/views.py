from functools import reduce
import json

from django.conf import settings
from django.http import Http404
from django.urls import reverse
from django.utils.functional import cached_property
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView

from .models import Layer, FilterField
from .permissions import LayerPermission
from .serializers import LayerSerializer

class LayerViewset(ModelViewSet):
    model = Layer
    serializer_class = LayerSerializer
    permission_classes = (LayerPermission, )

    def get_queryset(self):
        return self.model.objects.all()


class LayerViews(APIView):
    model = Layer
    DEFAULT_SOURCE_NAME = 'terra'
    DEFAULT_SOURCE_TYPE = 'vector'

    def get(self, request, slug, format=None):
        if slug not in settings.TERRA_LAYER_VIEWS:
            raise Http404('View does not exist')

        view = settings.TERRA_LAYER_VIEWS[slug]
        layers = self.layers(view['pk'])

        return Response(
            {
                'title': view['pk'],
                'layersTree': self.get_layers_tree(layers),
                'interactions': self.get_interactions(layers),
                'map': {
                        **settings.TERRA_DEFAULT_MAP_SETTINGS,
                        **{
                        'customStyle': {
                            'sources': [{
                                'id': self.DEFAULT_SOURCE_NAME,
                                'type': self.DEFAULT_SOURCE_TYPE,
                                'url': reverse('terra:group-tilejson',
                                                args=(layers[0].source.get_layer().group, ))
                            }],
                            'layers': self.get_map_layers(layers),
                        },
                    }
                }
            }
        )

    def get_map_layers(self, layers):
        return [{
            **layer.layer_style,
            **{
                'source': self.DEFAULT_SOURCE_NAME,
                'id': layer.layer_id,
                'source-layer': layer.source.name,
            }
        } for layer in layers]

    def get_interactions(self, layers):
        interactions = []
        for layer in layers:
            interactions += self.get_interactions_for_layer(layer)
        return interactions

    def get_interactions_for_layer(self, layer):
        interactions = []

        if layer.popup_enable:
            interactions.append({
                'id': layer.layer_id,
                'interaction': 'displayTooltip',
                'trigger': 'mouseover',
                'template': layer.popup_template,
                'constraints': [{
                    'minZoom': layer.popup_minzoom,
                    'maxZoom': layer.popup_maxzoom,
                },]
            })

        if layer.minisheet_enable:
            interactions.append({
                'id': layer.layer_id,
                'interaction': 'displayDetails',
                'template': layer.minisheet_template,
                'fetchProperties': {
                    'url': reverse('terra:feature-detail', args=(layer.source.name, '{{id}}')),
                    'id': '_id',
                },
            })

        return interactions

    def get_layers_tree(self, layers):
        layer_tree = []
        for layer in layers:
            try:
                layer_path, layer_name = layer.name.rsplit('/', 1)
            except ValueError:
                layer_path, layer_name = '', layer.name

            layer_object = {
                'label': layer_name,
                'initialState': {
                    'active': False,
                    'opacity': 1,
                },
                'layers': [layer.layer_id, ],
                'filters': {
                    'layer': layer.source.name,
                    # 'mainField': None, # TODO: find the mainfield
                    'fields': self.get_filter_fields_for_layer(layer),
                    'forms': self.get_filter_forms_for_layer(layer),
                }
            }
            # layer_tree.append(layer_object)
            self.insert_layer_in_path(layer_tree, layer_path, layer_object)
        return layer_tree

    def insert_layer_in_path(self, layer_tree, path, layer):
        try:
            current_path, sub_path = path.split('/', 1)
        except ValueError:
            # It's final path, create it and return
            current_path = path
            sub_path = None

        try:
            group_layers = reduce(lambda x: x['group'] == current_path, layer_tree)
        except TypeError:
            # Layer does not exist, create it and follow
            group_layers = {
                'group': current_path,
                'layers': [],
            }
            layer_tree.append(group_layers)

        if sub_path:
            return self.insert_layer_in_path(group_layers['layers'], sub_path, layer)
        else:
            group_layers['layers'].append(layer)

        return layer_tree

    def get_filter_fields_for_layer(self, layer):
        return [
            {
                'property': field_filter.field.name,
                'label': field_filter.field.label,
            }
            for field_filter in FilterField.objects.filter(layer=layer)
        ]

    def get_filter_forms_for_layer(self, layer):
        return [
            {
                'property': field_filter.field.name,
                'label': field_filter.field.label,
                'type': field_filter.filter_type,
                # 'fetchValues': true, TODO: When front provide the information
            }
            for field_filter in FilterField.objects.filter(layer=layer)
        ]

    def layers(self, pk):
        layers = self.model.objects.filter(view=pk)
        if layers:
            return layers
        raise Http404
