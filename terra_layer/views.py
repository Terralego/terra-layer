from django.conf import settings
from django.core.cache import cache
from django.db.models import Prefetch
from django.http import Http404
from django.urls import reverse
from django.utils.http import urlunquote
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView

from .models import Layer, LayerGroup, FilterField
from .permissions import LayerPermission
from .serializers import LayerSerializer
from .sources_serializers import SourceSerializer
from .utils import dict_merge, get_layer_group_cache_key


class LayerViewset(ModelViewSet):
    model = Layer
    serializer_class = LayerSerializer
    ordering_fields = filter_fields = ('source', 'group', 'name', 'order',
                                       'table_enable', 'popup_enable', 'minisheet_enable')
    permission_classes = (LayerPermission, )

    def get_queryset(self):
        return self.model.objects.all()


class LayerViews(APIView):
    permission_classes = ()
    model = Layer
    DEFAULT_SOURCE_NAME = 'terra'
    DEFAULT_SOURCE_TYPE = 'vector'

    prefetch_layers = Prefetch('layers', (
        Layer.objects
        .select_related('source')
        .prefetch_related(
            Prefetch(
                'fields_filters',
                FilterField.objects.filter(shown=True).select_related('field'),
                to_attr='filters_shown'
            ),
            Prefetch(
                'fields_filters',
                FilterField.objects.filter(filter_enable=True).select_related('field'),
                to_attr='filters_enabled'
            ),
            'custom_styles__source',
        )
    ))

    view = None

    def get(self, request, slug=None, format=None):
        if slug is None:
            return Response(settings.TERRA_LAYER_VIEWS)

        if slug not in settings.TERRA_LAYER_VIEWS:
            raise Http404('View does not exist')

        self.view = settings.TERRA_LAYER_VIEWS[slug]

        cache_key = get_layer_group_cache_key(self.view['pk'])
        return Response(cache.get_or_set(cache_key, self.get_layer_structure))

    def get_layer_structure(self):
        layers = self.layers(self.view['pk'])
        return {
            'title': self.view['name'],
            'type': self.view.get('type', 'default'),
            'layersTree': self.get_layers_tree(self.view),
            'interactions': self.get_interactions(layers),
            'map': {
                **settings.TERRA_DEFAULT_MAP_SETTINGS,
                'customStyle': {
                    'sources': [{
                        'id': self.DEFAULT_SOURCE_NAME,
                        'type': self.DEFAULT_SOURCE_TYPE,
                        'url': reverse(
                            'geostore:group-tilejson',
                            args=(layers.first().source.get_layer().layer_groups.first().slug,)
                        )
                    }],
                    'layers': self.get_map_layers(layers),
                },
            }
        }

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

    def get_formatted_interactions(self, layer):
        return [
            {
                'id': layer.layer_identifier,
                'fetchProperties': {
                    'url': urlunquote(reverse('geostore:feature-detail', args=(layer.source.get_layer().pk, '{{id}}'))),
                    'id': '_id',
                },
                **interaction,
            }
            for interaction in layer.interactions
        ]

    def get_interactions_for_layer(self, layer):
        interactions = self.get_formatted_interactions(layer)
        for cs in layer.custom_styles.all():
            interactions += self.get_formatted_interactions(cs)

        if layer.popup_enable:
            interactions.append({
                'id': layer.layer_identifier,
                'interaction': 'displayTooltip',
                'trigger': 'mouseover',
                'template': layer.popup_template,
                'constraints': [{
                    'minZoom': layer.popup_minzoom,
                    'maxZoom': layer.popup_maxzoom,
                }]
            })

        if layer.minisheet_enable:
            settings_interactions = {
                'id': layer.layer_identifier,
                'interaction': 'displayDetails',
                'template': layer.minisheet_template,
                'fetchProperties': {
                    'url': urlunquote(
                        reverse('geostore:feature-detail', args=(layer.source.get_layer().pk, '{{id}}'))),
                    'id': '_id',
                },
            }
            if layer.highlight_color:
                settings_interactions['highlight_color'] = layer.highlight_color

            interactions.append(settings_interactions)

        return interactions

    def get_layers_list_for_layer(self, layer):
        return [
            layer.layer_identifier,
            *[s.layer_identifier for s in layer.custom_styles.all()]
        ]

    def get_layers_tree(self, view):
        layer_tree = []
        for group in LayerGroup.objects.filter(view=view['pk'], parent=None).prefetch_related(
                self.prefetch_layers
        ):
            layer_tree.append(self.get_tree_group(group))
        return layer_tree

    def get_tree_group(self, group):
        group_content = {
            'group': group.label,
            'exclusive': group.exclusive,
            'selectors': group.selectors,
            'layers': [],
            **group.settings,
        }

        # Add subgroups
        for sub_group in group.children.filter(view=group.view).prefetch_related(self.prefetch_layers):
            group_content['layers'].append(self.get_tree_group(sub_group))

        # Add layers of group
        for layer in group.layers.filter(in_tree=True):

            default_values = {
                'initialState': {
                    'active': False,
                    'opacity': 1,
                },
            }

            main_field = getattr(layer.main_field, 'name', None)

            layer_object = {
                **dict_merge(default_values, layer.settings),
                'label': layer.name,
                'content': layer.description,
                'layers': self.get_layers_list_for_layer(layer),
                'legends': layer.legends,
                'mainField': main_field,
                'filters': {
                    'layer': layer.source.slug,
                    'mainField': main_field,
                    'fields': self.get_filter_fields_for_layer(layer),
                    'form': self.get_filter_forms_for_layer(layer),
                },
            }

            layer_object['filters']['exportable'] = any([
                f['exportable']
                for f in layer_object['filters']['fields'] or []
            ])

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

    def get_filter_fields_for_layer(self, layer):
        if layer.table_enable:
            return [
                {
                    'value': field_filter.field.name,
                    'label': field_filter.label or field_filter.field.label,
                    'exportable': field_filter.exportable,
                    'format_type': field_filter.format_type,
                }
                for field_filter in layer.filters_shown
            ]

    def get_filter_forms_for_layer(self, layer):
        if layer.filters_enabled:
            return [
                {
                    'property': field_filter.field.name,
                    'label': field_filter.label or field_filter.field.label,
                    **field_filter.filter_settings,
                }
                for field_filter in layer.filters_enabled
            ]

    def layers(self, pk):
        layers = (
            self.model.objects
                .filter(group__view=pk)
                .order_by('order')
                .select_related('source')
                .prefetch_related(
                    'custom_styles__source'
                )
        )
        if layers:
            return layers
        raise Http404
