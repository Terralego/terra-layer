from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files import File
from django.test import TestCase
from django.urls import reverse
from django_geosource.models import PostGISSource, FieldTypes
from PIL import Image
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from rest_framework.test import APIClient

from terra_layer.models import Layer, LayerGroup, FilterField, Scene

from .factories import SceneFactory

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

        layer_from_group = [
            layer for layer in response.json() if layer["group"] == group.id
        ]

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
            group=group, source=self.source, minisheet_enable=False
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
            "minisheet_enable": True,
            "filter_enable": True,
        }

        response = self.client.patch(reverse("layer-detail", args=[layer.pk]), query)

        self.assertEqual(response.status_code, HTTP_200_OK)

        response = response.json()
        self.assertTrue(response.get("minisheet_enable"))
        self.assertEqual(response["view"], self.scene.id)

    def test_create_empty_tree_scene(self):
        query = {
            "name": "Scene Name",
            "category": "map",
            "tree": [],
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
                    "title": "Scene Group name",
                    "group": True,
                    "expanded": True,
                    "children": [],
                },
            ],
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = response.json()

        self.assertEqual(len(response.get("tree")), 1)

        group = LayerGroup.objects.get(label="Scene Group name", view=response["id"])
        self.assertEqual(group.view.pk, response["id"])

    def test_create_scene_with_layer_in_tree(self):

        layer = Layer.objects.create(
            group=None, source=self.source, minisheet_enable=False
        )
        query = {
            "name": "Scene Name",
            "category": "map",
            "tree": [{"geolayer": layer.id},],
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = response.json()

        self.assertEqual(len(response.get("tree")), 1)

        layer.refresh_from_db()

        self.assertEqual(layer.group.label, "Unknown")

    def test_create_scene_with_complexe_tree(self):
        layers = [
            Layer.objects.create(source=self.source, name=f"Layer {x}")
            for x in range(6)
        ]

        COMPLEXE_SCENE_TREE = [
            {
                "title": "My Group 1",
                "group": True,
                "children": [
                    {"geolayer": layers[0].id},
                    {"geolayer": layers[1].id},
                    {
                        "title": "Sub group 1",
                        "group": True,
                        "expanded": True,
                        "children": [{"geolayer": layers[2].id,}],
                    },
                    {"geolayer": layers[3].id},
                ],
            },
            {
                "title": "My group 2",
                "group": True,
                "children": [{"geolayer": layers[4].id,}],
            },
            {"geolayer": layers[5].id,},
        ]

        query = {
            "name": "Scene Name",
            "category": "map",
            "tree": COMPLEXE_SCENE_TREE,
        }

        response = self.client.post(reverse("scene-list"), query)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        scene = response.json()

        self.assertEqual(len(scene.get("tree")), 3)

        groups = LayerGroup.objects.filter(view=scene["id"])
        self.assertEqual(len(groups), 4)

        """group1 = LayerGroup.objects.get(view=scene["id"], label="My Group 1")
        groupsub1 = LayerGroup.objects.get(view=scene["id"], label="Sub group 1")
        group2 = LayerGroup.objects.get(view=scene["id"], label="My group 2")
        self.assertTrue(group1.order < groupsub1.order)
        self.assertTrue(groupsub1.order < group2.order)
        self.assertTrue(group1.order < group2.order)"""

        # Now test tree generation
        response = self.client.get(reverse("layerview", args=[scene["slug"]]))
        layersTree = response.json()
        #from pprint import pprint

        #pprint(layersTree)
        self.assertEqual(layersTree["title"], scene["name"])
        self.assertEqual(
            layersTree["layersTree"][0]["group"], scene["tree"][0]["title"]
        )
        self.assertEqual(
            layersTree["layersTree"][1]["group"], scene["tree"][1]["title"]
        )
        # self.assertEqual(layersTree["layersTree"][2]["group"], layers[5].name)

