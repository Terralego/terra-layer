from django.conf import settings
from django.core.cache import cache
from django.db.models import Prefetch, Q
from django.http import Http404, QueryDict
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.http import urlunquote
from django_geosource.models import WMTSSource
from geostore.models import Layer as GeostoreLayer
from geostore.tokens import tiles_token_generator
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView

from ..models import Layer, LayerGroup, FilterField, Scene
from ..permissions import LayerPermission, ScenePermission
from ..serializers import LayerSerializer, SceneListSerializer, SceneDetailSerializer
from ..sources_serializers import SourceSerializer
from ..utils import dict_merge, get_layer_group_cache_key


class SceneViewset(ModelViewSet):
    model = Scene
    queryset = Scene.objects.all()
    permission_classes = (ScenePermission,)

    def get_serializer_class(self,):
        if self.action == "retrieve":
            return SceneDetailSerializer
        return SceneListSerializer


class LayerViewset(ModelViewSet):
    model = Layer
    serializer_class = LayerSerializer
    ordering_fields = filter_fields = (
        "source",
        "group",
        "name",
        "order",
        "table_enable",
        "popup_enable",
        "minisheet_enable",
    )
    permission_classes = (LayerPermission,)

    def get_queryset(self):
        return self.model.objects.all()


class LayerView(APIView):
    permission_classes = ()
    model = Layer
    EXTERNAL_SOURCES_CLASSES = [WMTSSource]
    DEFAULT_SOURCE_NAME = "terra"
    DEFAULT_SOURCE_TYPE = "vector"

    prefetch_layers = Prefetch(
        "layers",
        (
            Layer.objects.select_related("source").prefetch_related(
                Prefetch(
                    "fields_filters",
                    FilterField.objects.filter(shown=True).select_related("field"),
                    to_attr="filters_shown",
                ),
                Prefetch(
                    "fields_filters",
                    FilterField.objects.filter(filter_enable=True).select_related(
                        "field"
                    ),
                    to_attr="filters_enabled",
                ),
                "custom_styles__source",
            )
        ),
    )

    scene = None

    def get(self, request, slug=None, format=None):
        # Get all scene by default
        if slug is None:
            return Response(SceneListSerializer(Scene.objects.all(), many=True).data)

        self.scene = get_object_or_404(Scene, slug=slug)

        self.layergroup = self.layers.first().source.get_layer().layer_groups.first()
        self.user_groups = tiles_token_generator.get_groups_intersect(
            self.request.user, self.layergroup
        )

        cache_key = get_layer_group_cache_key(
            self.scene, self.user_groups.values_list("name", flat=True)
        )

        response = cache.get_or_set(cache_key, self.get_response_with_sources)
        return Response(response)

    def get_response_with_sources(self):
        layer_structure = self.get_layer_structure()

        tilejson_url = reverse("group-tilejson", args=(self.layergroup.slug,))
        querystring = QueryDict(mutable=True)
        if not self.request.user.is_anonymous:
            querystring.update(
                {
                    "idb64": tiles_token_generator.token_idb64(
                        self.user_groups, self.layergroup
                    ),
                    "token": tiles_token_generator.make_token(
                        self.user_groups, self.layergroup
                    ),
                }
            )

        layer_structure["map"]["customStyle"]["sources"] = [
            {
                "id": self.DEFAULT_SOURCE_NAME,
                "type": self.DEFAULT_SOURCE_TYPE,
                "url": f"{tilejson_url}?{querystring.urlencode()}",
            }
        ]
        return layer_structure

    def get_layer_structure(self):
        return {
            "title": self.scene.name,
            "type": self.scene.category,
            "layersTree": self.get_layers_tree(self.scene),
            "interactions": self.get_interactions(self.layers),
            "map": {
                **settings.TERRA_DEFAULT_MAP_SETTINGS,
                "customStyle": {"sources": [], "layers": self.get_map_layers()},
            },
        }

    def get_map_layers(self):
        map_layers = []
        for layer in self.layers.filter(source__slug__in=self.authorized_sources):
            map_layers += [
                SourceSerializer.get_object_serializer(layer).data,
                *[
                    SourceSerializer.get_object_serializer(cs).data
                    for cs in layer.custom_styles.filter(
                        source__slug__in=self.authorized_sources
                    )
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
                "id": layer.layer_identifier,
                "fetchProperties": {
                    "url": urlunquote(
                        reverse(
                            "feature-detail",
                            args=(layer.source.get_layer().pk, "{{id}}"),
                        )
                    ),
                    "id": "_id",
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
            interactions.append(
                {
                    "id": layer.layer_identifier,
                    "interaction": "displayTooltip",
                    "trigger": "mouseover",
                    "template": layer.popup_template,
                    "constraints": [
                        {"minZoom": layer.popup_minzoom, "maxZoom": layer.popup_maxzoom}
                    ],
                }
            )

        if layer.minisheet_enable:
            settings_interactions = {
                "id": layer.layer_identifier,
                "interaction": "displayDetails",
                "template": layer.minisheet_template,
                "fetchProperties": {
                    "url": urlunquote(
                        reverse(
                            "feature-detail",
                            args=(layer.source.get_layer().pk, "{{id}}"),
                        )
                    ),
                    "id": "_id",
                },
            }
            if layer.highlight_color:
                settings_interactions["highlight_color"] = layer.highlight_color

            interactions.append(settings_interactions)

        return interactions

    def get_layers_list_for_layer(self, layer):
        return [
            layer.layer_identifier,
            *[s.layer_identifier for s in layer.custom_styles.all()],
        ]

    def get_layers_tree(self, scene):
        layer_tree = []
        for group in LayerGroup.objects.filter(
            view=scene, parent=None
        ).prefetch_related(self.prefetch_layers):
            layer_tree.append(self.get_tree_group(group))
        return layer_tree

    def get_tree_group(self, group):
        group_content = {
            "group": group.label,
            "exclusive": group.exclusive,
            "selectors": group.selectors,
            "layers": [],
            **group.settings,
        }

        # Add subgroups
        for sub_group in group.children.filter(view=group.view).prefetch_related(
            self.prefetch_layers
        ):
            group_content["layers"].append(self.get_tree_group(sub_group))

        # Add layers of group
        for layer in group.layers.filter(in_tree=True):
            if (
                layer.source.slug not in self.authorized_sources
                or layer.custom_styles.exclude(
                    source__slug__in=self.authorized_sources
                ).exists()
            ):
                # Exclude layers with non-authorized sources
                continue

            default_values = {"initialState": {"active": False, "opacity": 1}}

            main_field = getattr(layer.main_field, "name", None)

            layer_object = {
                **dict_merge(default_values, layer.settings),
                "label": layer.name,
                "content": layer.description,
                "layers": self.get_layers_list_for_layer(layer),
                "legends": layer.legends,
                "mainField": main_field,
                "filters": {
                    "layer": layer.source.slug,
                    "mainField": main_field,
                    "fields": self.get_filter_fields_for_layer(layer),
                    "form": self.get_filter_forms_for_layer(layer),
                },
            }

            layer_object["filters"]["exportable"] = any(
                [f["exportable"] for f in layer_object["filters"]["fields"] or []]
            )

            group_content["layers"].append(layer_object)

        return group_content

    def insert_layer_in_path(self, layer_tree, path, layer):

        try:
            current_path, sub_path = path.split("/", 1)
        except ValueError:
            # It's final path, create it and return
            current_path = path
            sub_path = None

        try:
            group_layers = next(
                filter(
                    lambda x: "group" in x and x.get("group") == current_path,
                    layer_tree,
                )
            )
        except StopIteration:
            # Layer does not exist, create it and follow
            group_layers = {"group": current_path, "layers": []}
            layer_tree.append(group_layers)

        if sub_path:
            return self.insert_layer_in_path(group_layers["layers"], sub_path, layer)
        else:
            group_layers["layers"].append(layer)

        return layer_tree

    def get_filter_fields_for_layer(self, layer):
        if layer.table_enable:
            return [
                {
                    "value": field_filter.field.name,
                    "label": field_filter.label or field_filter.field.label,
                    "exportable": field_filter.exportable,
                    "format_type": field_filter.format_type,
                }
                for field_filter in layer.filters_shown
            ]

    def get_filter_forms_for_layer(self, layer):
        if layer.filters_enabled:
            return [
                {
                    "property": field_filter.field.name,
                    "label": field_filter.label or field_filter.field.label,
                    **field_filter.filter_settings,
                }
                for field_filter in layer.filters_enabled
            ]

    @cached_property
    def authorized_sources(self):
        groups = self.user_groups
        sources_slug = list(
            self.layergroup.layers.filter(
                Q(authorized_groups__isnull=True) | Q(authorized_groups__in=groups)
            ).values_list("name", flat=True)
        ) + list(WMTSSource.objects.values_list("slug", flat=True))

        return sources_slug

    @cached_property
    def layers(self):
        layers = (
            self.model.objects.filter(group__view=self.scene.pk)
            .order_by("order")
            .select_related("source")
            .prefetch_related("custom_styles__source")
        )

        if layers:
            return layers
        raise Http404
