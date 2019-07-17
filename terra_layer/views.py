from functools import reduce
import json

from django.conf import settings
from django.http import Http404
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.http import urlunquote
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView

from .models import Layer, LayerGroup, FilterField
from .permissions import LayerPermission
from .serializers import LayerSerializer
from .sources_serializers import SourceSerializer


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

    def get(self, request, slug=None, format=None):
        if slug is None:
            return Response(settings.TERRA_LAYER_VIEWS)

        if slug not in settings.TERRA_LAYER_VIEWS:
            raise Http404('View does not exist')

        view = settings.TERRA_LAYER_VIEWS[slug]
        layers = self.layers(view['pk'])

        return Response(
            {
                'title': view['name'],
                'type': view.get('type', 'default'),
                'layersTree': self.get_layers_tree(view),
                'interactions': self.get_interactions(layers),
                'map': {
                    **settings.TERRA_DEFAULT_MAP_SETTINGS,
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
        )

    def get_map_layers(self, layers):
        map_layers = []
        for layer in layers:
            map_layers += [
                SourceSerializer.get_object_serializer(layer).data,
                *[
                    SourceSerializer.get_object_serializer(cs).data
                    for cs in layer.custom_styles.all()
                ],
            ]
        return map_layers

    def get_interactions(self, layers):
        interactions = []
        for layer in layers:
            interactions += self.get_interactions_for_layer(layer)
        return interactions

    def get_formatted_interactions(self, layer_id, interactions):
        return [
            {
                'id': layer_id,
                **interaction,
            }
            for interaction in interactions
        ]

    def get_interactions_for_layer(self, layer):
        interactions = self.get_formatted_interactions(layer.layer_identifier, layer.interactions)
        for cs in layer.custom_styles.all():
            interactions += self.get_formatted_interactions(cs.layer_identifier, cs.interactions)

        if layer.popup_enable:
            interactions.append({
                'id': layer.layer_identifier,
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
                'id': layer.layer_identifier,
                'interaction': 'displayDetails',
                'template': layer.minisheet_template,
                'fetchProperties': {
                    'url': urlunquote(reverse('terra:feature-detail', args=(layer.source.get_layer().pk, '{{id}}'))),
                    'id': '_id',
                },
            })

        return interactions

    def get_layers_list_for_layer(self, layer):
        return [
            layer.layer_identifier,
            *[s.layer_identifier for s in layer.custom_styles.all()]
        ]

    def get_layers_tree(self, view):
        layer_tree = []
        for group in LayerGroup.objects.filter(view=view['pk'], parent=None):
            layer_tree.append(self.get_tree_group(group))
        return layer_tree

    def get_tree_group(self, group):
        group_content = {
            'group': group.label,
            'exclusive': group.exclusive,
            'layers': [],
        }

        # Add subgroups
        for sub_group in LayerGroup.objects.filter(view=group.view, parent=group):
            group_content['layers'].append(self.get_tree_group(sub_group))

        # Add layers of group
        for layer in group.layers.all():
            layer_object = {
                **layer.settings,
                'label': layer.name,
                'initialState': {
                    'active': False,
                    'opacity': 1,
                },
                'content': layer.description,
                'layers': self.get_layers_list_for_layer(layer),
                'legends': layer.legends,
                'filters': {
                    'layer': layer.source.slug,
                    'mainField': self.get_filters_mainfield(layer),
                    'fields': self.get_filter_fields_for_layer(layer),
                    'form': self.get_filter_forms_for_layer(layer),
                },
            }

            layer_object['filters']['exportable'] = any([f['exportable'] for f in layer_object['filters']['fields'] or []])

            group_content['layers'].append(layer_object)

        return group_content

    def insert_layer_in_path(self, layer_tree, path, layer):

        try:
            current_path, sub_path = path.split('/', 1)
        except ValueError:
            # It's final path, create it and return
            current_path = path
            sub_path = None

        try:
            group_layers = next(filter(lambda x: 'group' in x and x.get('group') == current_path, layer_tree))
        except StopIteration:
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

    def get_filters_mainfield(self, layer):
        try:
            return layer.settings['filters']['mainField']
        except KeyError:
            return None

    def get_filter_fields_for_layer(self, layer):
        if layer.table_enable:
            return [
                {
                    'value': field_filter.field.name,
                    'label': field_filter.label or field_filter.field.label,
                    'exportable': field_filter.exportable,
                }
                for field_filter in FilterField.objects.filter(layer=layer, shown=True)
            ]

    def get_filter_forms_for_layer(self, layer):
        filter_fields = FilterField.objects.filter(layer=layer, filter_enable=True)
        if filter_fields.count() > 0:
            return [
                {
                    'property': field_filter.field.name,
                    'label': field_filter.label or field_filter.field.label,
                    **field_filter.filter_settings,
                }
                for field_filter in filter_fields
            ]

    def layers(self, pk):
        layers = self.model.objects.filter(group__view=pk).order_by('order')
        if layers:
            return layers
        raise Http404
