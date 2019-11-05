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
        self.assertEqual(Layer.objects.count(), len(response.json()))

    def test_create_layer(self):
        query = {
            "source": self.source.pk,
            "view": self.scene.pk,
            "name": "test layer",
            "table_export_enable": True,
            "filter_enable": False,
        }

        response = self.client.post(reverse("layer-list"), query)
        self.assertEqual(HTTP_201_CREATED, response.status_code)

        response = response.json()

        self.assertTrue(response.get("table_export_enable"))
        self.assertFalse(response.get("filter_enable"))
        self.assertEqual(response["view"], self.scene.id)

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
            "view": self.scene.pk,
            "name": "test layer",
            "minisheet_enable": True,
            "filter_enable": True,
        }

        response = self.client.patch(reverse("layer-detail", args=[layer.pk]), query)

        self.assertEqual(response.status_code, HTTP_200_OK)

        response = response.json()
        self.assertTrue(response.get("minisheet_enable"))
        self.assertEqual(response["view"], self.scene.id)
