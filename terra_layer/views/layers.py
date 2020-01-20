from django.conf import settings
from django.core.cache import cache
from django.db.models import Prefetch, Q
from django.http import Http404, QueryDict
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.http import urlunquote
from django_geosource.models import WMTSSource
from geostore.tokens import tiles_token_generator
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.serializers import ValidationError

from ..models import Layer, LayerGroup, FilterField, Scene
from ..permissions import LayerPermission, ScenePermission
from ..serializers import (
    LayerListSerializer,
    LayerDetailSerializer,
    SceneListSerializer,
    SceneDetailSerializer,
)
from ..sources_serializers import SourceSerializer
from ..utils import dict_merge, get_layer_group_cache_key


class SceneViewset(ModelViewSet):
    model = Scene
    queryset = Scene.objects.all()
    permission_classes = (ScenePermission,)

    def get_serializer_class(self,):
        if self.action in ["retrieve", "update", "create", "partial_update"]:
            return SceneDetailSerializer
        return SceneListSerializer

    def check_layer_status(self, view_id, current_node):
        """
        Check all layers in tree to valide existence and scene ownership.
        Recursive process.

        :param current_node: Current node from the tree
        """

        for item in current_node:
            if "geolayer" in item:
                try:
                    # Is layer deleted ?
                    layer = Layer.objects.get(pk=item["geolayer"])
                except Layer.DoesNotExist:
                    raise ValidationError(
                        f"Layer {item['geolayer']} doesn't exists anymore"
                    )

                # Is layer owned by another scene ?
                if layer.group and layer.group.view.id != view_id:
                    raise ValidationError(
                        f"Layer {item['geolayer']} can't be stolen from another scene"
                    )
            else:
                # And we start with the new node
                self.check_layer_status(view_id, item["children"])

    def perform_update(self, serializer):
        if serializer.is_valid():
            self.check_layer_status(
                serializer.instance.id, serializer.validated_data.get("tree", [])
            )
            serializer.save()

    def perform_create(self, serializer):
        if serializer.is_valid():
            self.check_layer_status(None, serializer.validated_data.get("tree", []))
            serializer.save()


class LayerViewset(ModelViewSet):
    model = Layer
    ordering_fields = (
        "name",
        "source__name",
        "group__view__name",
        "active_by_default",
        "order",
        "in_tree",
    )
    filter_fields = (
        "source",
        "group",
        "active_by_default",
        "in_tree",
        "table_enable",
        "popup_enable",
        "minisheet_enable",
    )
    permission_classes = (LayerPermission,)
    search_fields = ["name", "settings"]

    def get_queryset(self):
        return self.model.objects.all()

    def get_serializer_class(self,):
        if self.action in ["retrieve", "update", "create", "partial_update"]:
            return LayerDetailSerializer
        return LayerListSerializer

    def perform_destroy(self, instance):
        if instance.group:  #  Prevent deletion of layer used in any layer tree
            raise ValidationError("Can't delete a layer linked to a scene")
        super().perform_destroy(instance)


class LayerView(APIView):
    """ This view generates the LayersTree used to construct the frontend
    """

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
        """ Return a response object containing the full layersTree with updated
        user authentication.
        """

        layer_structure = self.get_layer_structure()

        tilejson_url = reverse("group-tilejson", args=(self.layergroup.slug,))
        querystring = QueryDict(mutable=True)

        # When the user is not anonymous, we provide tokens in the URL to authenticated
        # it in the MVT endpoint
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
        """ Return the structured layerTree
        """
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
        """ Return sources informations using serializer from sources_serializers module
        """
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
        """ Return interactions for all layers in the scene
        """
        interactions = []
        for layer in layers:
            interactions += self.get_interactions_for_layer(layer)
        return interactions

    def get_formatted_interactions(self, layer):
        """ Return all interactions of a layer after beeing formatted correctly
        for the frontend
        """
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
        """ Return formatted interaction of a layer

        It contains, popup, minisheet and custom styles
        """
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
        """ Return list of sublayers of a layer
        """
        return [
            layer.layer_identifier,
            *[s.layer_identifier for s in layer.custom_styles.all()],
        ]

    def get_layers_tree(self, scene):
        """ Return the full layer tree of a scene object
        """
        root_group = LayerGroup.objects.prefetch_related(self.prefetch_layers).get(
            view=scene, parent=None
        )

        # Keep only child of root group
        return self.get_group_dict(root_group)["layers"]

    def get_group_dict(self, group):
        """ Recursive method that return the tree from a LayerGroup element.

        `group.settings` is injected in the group dictionnary, so any setting can be overridden.

        """
        group_content = {
            "group": group.label,
            "exclusive": group.exclusive,
            "selectors": group.selectors,
            "order": group.order,
            "layers": [],
            **group.settings,
        }

        # Add subgroups
        for sub_group in group.children.filter(view=group.view).prefetch_related(
            self.prefetch_layers
        ):
            group_dict = self.get_group_dict(sub_group)
            # exclude empty groups
            if group_dict["layers"]:
                group_content["layers"].append(group_dict)

        # Add layers of group
        for layer in group.layers.filter(in_tree=True):
            layer_dict = self.get_layer_dict(layer)
            if layer_dict:
                group_content["layers"].append(layer_dict)

        # Group en layer ordering
        group_content["layers"].sort(key=lambda x: x["order"])

        # Remove key order as not part of schema
        [item.pop("order") for item in group_content["layers"]]

        return group_content

    def get_layer_dict(self, layer):
        if (
            layer.source.slug not in self.authorized_sources
            or layer.custom_styles.exclude(
                source__slug__in=self.authorized_sources
            ).exists()
        ):
            # Exclude layers with non-authorized sources
            return None

        default_values = {
            "initialState": {"active": layer.active_by_default, "opacity": 1}
        }

        main_field = getattr(layer.main_field, "name", None)

        # Construct the layer object
        layer_object = {
            **dict_merge(default_values, layer.settings),
            "label": layer.name,
            "order": layer.order,
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

        # Set the exportable status of the layer if any filter fields is exportable
        layer_object["filters"]["exportable"] = any(
            [f["exportable"] for f in layer_object["filters"]["fields"] or []]
        )

        return layer_object

    def get_filter_fields_for_layer(self, layer):
        """ Return the filter fields of the layer if table is enabled
        """
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
        """ Return forms of a layer if filters are enabled
        """
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
        """ Cached property of authorized sources from the authenticated user's groups
        """
        groups = self.user_groups
        sources_slug = list(
            self.layergroup.layers.filter(
                Q(authorized_groups__isnull=True) | Q(authorized_groups__in=groups)
            ).values_list("name", flat=True)
        ) + list(WMTSSource.objects.values_list("slug", flat=True))

        return sources_slug

    @cached_property
    def layers(self):
        """ List of layers of the selected scene
        """
        layers = (
            self.model.objects.filter(group__view=self.scene.pk)
            .order_by("order")
            .select_related("source")
            .prefetch_related("custom_styles__source")
        )

        if layers:
            return layers
        raise Http404
