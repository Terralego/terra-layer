import io
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django_geosource.models import PostGISSource, Source, FieldTypes, WMTSSource
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_403_FORBIDDEN,
)
from rest_framework.test import APIClient, APITestCase

from terra_layer.models import Layer, LayerGroup, FilterField, CustomStyle
from terra_layer.utils import get_layer_group_cache_key

from .factories import SceneFactory

from geostore.tests.factories import LayerFactory
from geostore import GeometryTypes

UserModel = get_user_model()


class ModelSourceViewsetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.default_user = UserModel.objects.get_or_create(
            is_superuser=True, **{UserModel.USERNAME_FIELD: "testuser"}
        )[0]
        self.client.force_authenticate(self.default_user)

        self.scene = SceneFactory(name="test_scene")
        self.source = PostGISSource.objects.create(
            name="test_view",
            db_name="test",
            db_password="test",
            db_host="localhost",
            geom_type=1,
            refresh=-1,
        )

    def test_list_view(self):
        # Create many sources and list them
        group = LayerGroup.objects.create(view=self.scene, label="Test Group")

        [Layer.objects.create(group=group, source=self.source) for x in range(5)]

        response = self.client.get(reverse("layer-list"))
        self.assertEqual(response.status_code, HTTP_200_OK)

        self.assertEqual(Layer.objects.count(), len(response.json()))

    def test_create_layer(self):
        query = {
            "source": self.source.pk,
            "name": "test layer",
            "table_export_enable": True,
            "filter_enable": False,
        }

        response = self.client.post(reverse("layer-list"), query)
        self.assertEqual(HTTP_201_CREATED, response.status_code)

        response = response.json()

        self.assertTrue(response.get("table_export_enable"))
        self.assertFalse(response.get("filter_enable"))
        self.assertEqual(response["view"], None)

    def test_update_layer(self):
        group = LayerGroup.objects.create(view=self.scene, label="Test Group")

        field = self.source.fields.create(
            name="test_field", label="test_label", data_type=FieldTypes.String.value
        )
        layer = Layer.objects.create(
            group=group,
            source=self.source,
            minisheet_config={"enable": False},
        )
        FilterField.objects.create(
            label="test layer fields",
            layer=layer,
            field=field,
            filter_settings={},
            filter_enable=True,
        )

        query = {
            "source": self.source.pk,
            "name": "test layer",
            "minisheet_config": {"enable": True},
            "filter_enable": True,
        }

        response = self.client.patch(reverse("layer-detail", args=[layer.pk]), query)

        self.assertEqual(response.status_code, HTTP_200_OK)

        response = response.json()
        self.assertTrue(response.get("minisheet_config", {}).get("enable"))
        self.assertEqual(response["view"], self.scene.id)

    def test_get_scene(self):
        response = self.client.get(reverse("scene-list"))
        self.assertEqual(response.status_code, HTTP_200_OK)
        response = response.json()
        self.assertEqual(response[0].get("name"), "test_scene")

    def test_create_empty_tree_scene(self):
        query = {
            "name": "Scene Name",
            "category": "map",
            "tree": [],
            "baselayer": [],
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = response.json()

        self.assertEqual(response.get("name"), "Scene Name")
        self.assertEqual(len(response.get("tree")), 0)
        # Slug should be autogenerated
        self.assertEqual(response.get("slug"), "scene-name")

        # Check slug at creation
        query = {
            "name": "Scene Name 2",
            "slug": "myslug",
            "category": "map",
            "baselayer": [],
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = response.json()

        # Slug should not be autogenerated
        self.assertEqual(response.get("slug"), "myslug")

    def test_update_scene(self):
        query = {"slug": "my-newslug"}

        response = self.client.patch(
            reverse("scene-detail", args=[self.scene.pk]), query
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        response = response.json()

        self.assertEqual(response.get("slug"), "my-newslug")

        # Check slug at modification
        query = {"name": "New Name"}

        response = self.client.patch(
            reverse("scene-detail", args=[self.scene.pk]), query
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        response = response.json()

        self.assertEqual(response.get("slug"), "my-newslug")

    def test_create_scene_with_group_in_tree(self):

        query = {
            "name": "Scene Name",
            "category": "map",
            "tree": [
                {
                    "label": "Scene Group name",
                    "group": True,
                    "expanded": True,
                    "children": [],
                },
            ],
            "baselayer": [],
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = response.json()

        self.assertEqual(len(response.get("tree")), 1)

        group = LayerGroup.objects.get(label="Scene Group name", view=response["id"])
        self.assertEqual(group.view.pk, response["id"])

    def test_create_scene_with_layer_in_tree(self):

        layer = Layer.objects.create(
            group=None, source=self.source, minisheet_config={"enable": False}
        )
        query = {
            "name": "Scene Name",
            "category": "map",
            "tree": [{"geolayer": layer.id}],
            "baselayer": [],
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = response.json()

        self.assertEqual(len(response.get("tree")), 1)

        layer.refresh_from_db()

        self.assertEqual(layer.group.label, "Root")

    def test_layer_view_with_source_model(self):
        source = Source.objects.create(
            geom_type=10,
            name="test_view_2",
        )
        layer = Layer.objects.create(
            source=source,
            name="Layer",
            id=1,
        )

        query = {
            "name": "Scene Name",
            "category": "map",
            "tree": [{"geolayer": layer.id}],
            "baselayer": [],
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        scene = response.json()

        response = self.client.get(reverse("layerview", args=[scene["slug"]]))

        json_response = response.json()
        self.assertEqual(
            json_response["map"]["customStyle"]["layers"],
            [
                {
                    "id": "5f3f90d2aa8a14d5bb88c2f0bbf44610",
                    "layerId": 1,
                    "source": "terra",
                    "source-layer": "test_view_2",
                }
            ],
        )

    def test_layer_view_with_wmtsource(self):
        source = WMTSSource.objects.create(
            name="Titi",
            geom_type=1,
            tile_size=256,
            minzoom=14,
            maxzoom=15,
            url="http://www.test.test",
        )
        layer = Layer.objects.create(
            source=source,
            name="Layer",
            id=1,
        )

        query = {
            "name": "Scene Name",
            "category": "map",
            "tree": [{"geolayer": layer.id}],
            "baselayer": [],
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        scene = response.json()

        response = self.client.get(reverse("layerview", args=[scene["slug"]]))

        json_response = response.json()
        self.assertEqual(
            json_response["map"]["customStyle"]["layers"],
            [
                {
                    "id": "282d40e1ab9a059aa9d6eff431407e76",
                    "layerId": 1,
                    "type": "raster",
                    "minzoom": 14,
                    "maxzoom": 15,
                    "source": {
                        "type": "raster",
                        "tileSize": 256,
                        "tiles": ["http://www.test.test"],
                    },
                }
            ],
        )

    def test_layer_view_with_custom_style(self):
        layer = Layer.objects.create(
            source=self.source,
            name="Layer",
            interactions=[
                {
                    "id": "terralego-eae-sync",
                    "interaction": "highlight",
                    "trigger": "mouseover",
                },
            ],
            minisheet_config={
                "enable": True,
                "highlight_color": True,
            },
            popup_config={"enable": True},
        )
        CustomStyle.objects.create(
            layer=layer,
            source=self.source,
            interactions=[
                {"id": "custom_style", "interaction": "highlight", "trigger": "click"},
            ],
        )

        query = {
            "name": "Scene Name",
            "category": "map",
            "tree": [{"geolayer": layer.id}],
            "baselayer": [],
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        scene = response.json()

        response = self.client.get(reverse("layerview", args=[scene["slug"]]))
        layersTree = response.json()

        self.assertEqual(len(layersTree["interactions"]), 4)

    def test_layer_view_with_table_enable(self):
        field = self.source.fields.create(
            name="_test_field", label="test_label", data_type=FieldTypes.String.value
        )
        layer = Layer.objects.create(
            source=self.source,
            name="Layer",
            table_enable=True,
        )
        FilterField.objects.create(
            label="test layer fields",
            layer=layer,
            field=field,
            filter_settings={},
            filter_enable=True,
            shown=True,
            format_type="test",
            exportable=True,
        )
        query = {
            "name": "Scene Name",
            "category": "map",
            "tree": [{"geolayer": layer.id}],
            "baselayer": [],
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        scene = response.json()

        response = self.client.get(reverse("layerview", args=[scene["slug"]]))
        layersTree = response.json()

        self.assertEqual(
            layersTree["layersTree"][0]["filters"]["fields"][0],
            {
                "value": "_test_field",
                "label": "test layer fields",
                "exportable": True,
                "format_type": "test",
                "display": True,
                "settings": {},
            },
        )

    def test_layer_view_with_table_enable_no_layer(self):
        self.source.fields.create(
            name="_test_field", label="test_label", data_type=FieldTypes.String.value
        )
        layer = Layer.objects.create(
            source=self.source,
            name="Layer",
            table_enable=True,
        )
        query = {
            "name": "Scene Name",
            "category": "map",
            "tree": [{"geolayer": layer.id}],
            "baselayer": [],
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        scene = response.json()
        layer.delete()
        response = self.client.get(reverse("layerview", args=[scene["slug"]]))
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_create_scene_with_complexe_tree(self):
        layers = [
            Layer.objects.create(
                source=self.source,
                name=f"Layer {x}",
            )
            for x in range(7)
        ]

        COMPLEXE_SCENE_TREE = [
            {
                "label": "My Group 1",
                "group": True,
                "children": [
                    {"geolayer": layers[0].id},
                    {"geolayer": layers[1].id},
                    {
                        "label": "Sub group 1",
                        "group": True,
                        "expanded": True,
                        "children": [{"geolayer": layers[2].id}],
                    },
                    {"geolayer": layers[3].id},
                ],
            },
            {
                "label": "My group 2",
                "group": True,
                "children": [{"geolayer": layers[4].id}],
            },
            {"geolayer": layers[5].id},
            {
                "label": "My group 3",
                "group": True,
                "children": [{"geolayer": layers[6].id}],
            },
        ]

        query = {
            "name": "Scene Name",
            "category": "map",
            "tree": COMPLEXE_SCENE_TREE,
            "baselayer": [],
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        scene = response.json()

        self.assertEqual(len(scene.get("tree")), 4)

        groups = LayerGroup.objects.filter(view=scene["id"])
        self.assertEqual(len(groups), 5)

        # Get groups
        group1 = LayerGroup.objects.get(view=scene["id"], label="My Group 1")
        groupsub1 = LayerGroup.objects.get(view=scene["id"], label="Sub group 1")
        group2 = LayerGroup.objects.get(view=scene["id"], label="My group 2")

        # Refresh data
        [layer.refresh_from_db() for layer in layers]

        # Check order
        self.assertGreater(group2.order, group1.order)
        self.assertGreater(layers[3].order, groupsub1.order)

        # Now test tree generation
        response = self.client.get(reverse("layerview", args=[scene["slug"]]))
        layersTree = response.json()

        # Root tree test
        self.assertEqual(layersTree["title"], scene["name"])
        self.assertEqual(
            layersTree["layersTree"][0]["group"], scene["tree"][0]["label"]
        )
        self.assertEqual(
            layersTree["layersTree"][1]["group"], scene["tree"][1]["label"]
        )
        self.assertEqual(layersTree["layersTree"][2]["label"], layers[5].name)

        # Subgroup test
        self.assertEqual(
            layersTree["layersTree"][0]["layers"][0]["label"], layers[0].name
        )

        # Test final ordering also
        self.assertEqual(
            layersTree["layersTree"][0]["layers"][2]["group"],
            scene["tree"][0]["children"][2]["label"],
        )

        # Test last group with layer
        self.assertEqual(
            layersTree["layersTree"][3]["layers"][0]["label"], layers[6].name
        )

    def test_scene_with_import_file(self):
        layer = Layer.objects.create(source=self.source)

        SCENE_TREE = [
            {
                "label": "My Group 1",
                "group": True,
                "children": [{"geolayer": layer.id, "label": ""}],
            }
        ]

        query = {
            "name": "Scene Name",
            "category": "map",
            "tree": json.dumps(SCENE_TREE),
            "file": io.StringIO("a,b,c\n0,0,0"),
        }

        with patch("terra_layer.views.layers.call_command") as mock_call, patch(
            "terra_layer.views.layers.get_commands", return_value={"load_xls": "fake"}
        ):
            response = self.client.post(
                reverse("scene-list"), query, format="multipart"
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)
            self.assertEqual(mock_call.call_args[0], ("load_xls",))

            # Without file
            del query["file"]

            response = self.client.patch(
                reverse("scene-detail", args=[response.json()["id"]]),
                query,
                format="multipart",
            )

            self.assertEqual(response.status_code, HTTP_200_OK)

    def test_validation_error_on_scene_create(self):

        layer = Layer.objects.create(group=None, source=self.source)

        query = {
            "name": "Scene Name",
            "category": "map",
            "tree": [{"geolayer": layer.id}],
        }

        self.client.post(reverse("scene-list"), query)

        # Try to steal a layer from another scene
        query = {
            "name": "Another scene Name",
            "category": "map",
            "tree": [{"geolayer": layer.id}],
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        # Try to create a tree with a missing view
        query = {
            "name": "Yet another scene Name",
            "category": "map",
            "tree": [{"geolayer": 20000}],
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        # Try to create a tree with a wrong schema, group should be true or false
        query = {
            "name": "Yet another scene Name",
            "category": "map",
            "tree": [{"geolayer": layer.id, "group": 3}],
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_validation_error_on_delete_attached_layer(self):

        layer = Layer.objects.create(group=None, source=self.source)

        query = {
            "name": "Scene Name",
            "category": "map",
            "tree": [{"geolayer": layer.id}],
            "baselayer": [],
        }

        self.client.post(reverse("scene-list"), query)

        response = self.client.delete(reverse("layer-detail", kwargs={"pk": layer.id}))
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_delete_layer(self):
        layer = Layer.objects.create(
            group=None,
            source=self.source,
            minisheet_config={"enable": False},
        )

        response = self.client.delete(reverse("layer-detail", kwargs={"pk": layer.id}))
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)


class ModelSourceViewsetAnonymousTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.default_user = UserModel.objects.get_or_create(
            is_superuser=False, **{UserModel.USERNAME_FIELD: "testuser"}
        )[0]
        self.client.force_authenticate(self.default_user)

        self.scene = SceneFactory(name="test_scene")
        self.source = PostGISSource.objects.create(
            name="test_view",
            db_name="test",
            db_password="test",
            db_host="localhost",
            geom_type=1,
            refresh=-1,
        )

    def test_list_view_no_permission(self):
        group = LayerGroup.objects.create(view=self.scene, label="Test Group")

        [Layer.objects.create(group=group, source=self.source) for x in range(5)]

        response = self.client.get(reverse("layer-list"))
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_create_layer_no_permission(self):
        query = {
            "source": self.source.pk,
            "name": "test layer",
            "table_export_enable": True,
            "filter_enable": False,
        }

        response = self.client.post(reverse("layer-list"), query)
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_scene_list_no_permission(self):
        layer = Layer.objects.create(
            source=self.source,
            name="Layer",
            table_enable=True,
        )
        query = {
            "name": "Scene Name",
            "category": "map",
            "tree": [{"geolayer": layer.id}],
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_source_list_no_permission(self):
        layer = Layer.objects.create(
            source=self.source,
            name="Layer",
            table_enable=True,
        )
        query = {
            "name": "Scene Name",
            "category": "map",
            "tree": [{"geolayer": layer.id}],
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_source_creation_no_permission(self):
        source_example = {
            "_type": "PostGISSource",
            "name": "Test Source",
            "db_username": "username",
            "db_name": "dbname",
            "db_host": "hostname.com",
            "query": "SELECT 1",
            "geom_field": "geom",
            "refresh": -1,
            "geom_type": 1,
        }
        response = self.client.post(
            reverse("geosource:geosource-list"),
            {**source_example, "db_password": "test_password"},
            format="json",
        )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_geostore_no_permission(self):
        point_layer = LayerFactory(
            name="no schema point geom", geom_type=GeometryTypes.Point
        )
        response = self.client.post(
            reverse("feature-list", args=[point_layer.pk]),
            data={"geom": "POINT(0 0)", "properties": {"toto": "ok"}},
        )
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)


class LayerViewTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserModel.objects.create(
            **{UserModel.USERNAME_FIELD: "private_user"}
        )
        cls.source_params = {
            "name": "test_view",
            "db_name": "test",
            "db_password": "test",
            "db_host": "localhost",
            "geom_type": 1,
            "refresh": -1,
        }
        cls.scene = SceneFactory(name="test_scene")
        cls.layer_group = LayerGroup.objects.get(view=cls.scene)

    def test_cache_is_cleared_after_private_layer_update(self):
        group = Group.objects.create(name="private")
        group.user_set.add(self.user)
        source = PostGISSource.objects.create(
            **self.source_params, settings={"groups": [group.pk]}
        )
        layer = Layer.objects.create(
            name="private_layer", source=source, group=self.layer_group
        )
        # relationship is between geolayer and group, not "terralayer"
        geo_layer = source.get_layer()
        group.authorized_layers.add(geo_layer)

        self.client.force_authenticate(self.user)
        self.client.get(reverse("layerview", args=[self.scene.slug]))

        cache_key = get_layer_group_cache_key(
            self.scene,
            [
                group.name,
            ],
        )
        self.assertIsNotNone(cache.get(cache_key))

        # updating layer to trigger cache reset
        layer.name = "new_name"
        layer.save()
        self.assertIsNone(cache.get(cache_key))

    def test_cache_cleared_after_public_layer_update(self):
        source = PostGISSource.objects.create(**self.source_params)
        layer = Layer.objects.create(
            name="public_layer", source=source, group=self.layer_group
        )

        self.client.get(reverse("layerview", args=[self.scene.slug]))

        cache_key = get_layer_group_cache_key(self.scene)
        self.assertIsNotNone(cache.get(cache_key))

        # updating layer to trigger cache reset
        layer.name = "new_name"
        layer.save()
        self.assertIsNone(cache.get(cache_key))

    def test_cache_updated_with_query_parameter(self):
        source = PostGISSource.objects.create(**self.source_params)
        Layer.objects.create(name="public_layer", source=source, group=self.layer_group)

        self.client.get(reverse("layerview", args=[self.scene.slug]))

        cache_key = get_layer_group_cache_key(self.scene)
        self.assertIsNotNone(cache.get(cache_key))

        response = self.client.get(
            reverse("layerview", args=[self.scene.slug]), {"cache": "false"}
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
