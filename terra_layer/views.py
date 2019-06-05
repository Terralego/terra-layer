from functools import reduce

from django.utils.functional import cached_property
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView

from .models import Layer, FilterField
from .serializers import LayerSerializer

class LayerViewset(ModelViewSet):
    model = Layer
    serializer_class = LayerSerializer
    authentication_classes = ()

    def get_queryset(self):
        return self.model.objects.all()


class LayerViews(APIView):
    model = Layer

    def get(self, request, pk, format=None):
        view_response = {
            'title': 'View Title',
            'layersTree': self.get_layers_tree(pk),
            'interactions': [],
            'map': {}
        }

        return Response(view_response)

    def get_layers_tree(self, pk):
        layer_tree = []
        for layer in self.layers(pk):
            layer_path, layer_name = layer.name.rsplit('/', 1)

            layer_object = {
                'label': layer_name,
                'initialState': {
                    'active': False,
                    'opacity': 1,
                },
                'layers': [layer.source.name, ],
                'filters': [{
                    'layer': layer.source.name,
                    # 'mainField': None, # TODO: find the mainfield
                    'fields': self.get_filter_fields_for_layer(layer),
                    'forms': self.get_filter_forms_for_layer(layer),
                }]
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
        [
            {
                'property': field_filter.field.name,
                'label': field_filter.field.label,
                'type': field_filter.filter_type,
                # 'fetchValues': true, TODO: When front provide the information
            }
            for field_filter in FilterField.objects.filter(layer=layer)
        ]

    def layers(self, pk):
        return self.model.objects.filter(view=pk)
