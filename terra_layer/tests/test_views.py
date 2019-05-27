from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from rest_framework.test import APIClient

from django_geosource.models import PostGISSource
from terra_layer.models import Layer, FilterField

UserModel = get_user_model()


class ModelSourceViewsetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.default_user = UserModel.objects.get_or_create(**{UserModel.USERNAME_FIELD:'testuser'})[0]
        self.client.force_authenticate(self.default_user)

        self.source = PostGISSource.objects.create(name="test_view",
                                                   db_name="test",
                                                   db_password="test",
                                                   db_host="localhost",
                                                   geom_type=1,
                                                   refresh=-1)


    def test_list_view(self):
        # Create many sources and list them
        [
            Layer.objects.create(view=0, source=self.source)
            for x in range(5)
        ]

        response = self.client.get(reverse('terralayer:layer-list'))
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(
            Layer.objects.count(),
            len(response.json()['results'])
        )

    def test_create_layer(self):
        field = self.source.fields.create(name="test_field", label="test_label", data_type="string")
        field2 = self.source.fields.create(name="test_field2", label="test_label", data_type="integer")

        filter_field = {
            'field': field.pk,
            'filter_type': 42,
            'filter_settings': {
                'filter_test': 'filter_setting_value',
            }
        }

        query = {
            "source": self.source.pk,
            "view": 0,
            "name": "test layer",

            "table_fields": [field.pk, field2.pk],
            "table_export_fields": [field.pk, ],

            "filter_enable": True,
            "filter_fields": [filter_field, ]
        }

        response = self.client.post(reverse('terralayer:layer-list'), query)
        self.assertEqual(HTTP_201_CREATED, response.status_code)

        response = response.json()
        self.assertEqual(2, len(response.get('table_fields')))
        self.assertEqual(1, len(response.get('table_export_fields')))

        self.assertEqual(1, len(response.get('filter_fields')))
        self.assertDictContainsSubset(filter_field, response.get('filter_fields')[0])

    def test_update_layer(self):
        field = self.source.fields.create(name="test_field", label="test_label", data_type="string")
        layer = Layer.objects.create(view=0, source=self.source)
        layer.table_fields.add(field)
        FilterField.objects.create(layer=layer, field=field, filter_settings={}, filter_type=33)

        filter_field = {
            'field': field.pk,
            'filter_type': 42,
            'filter_settings': {
                'filter_test': 'filter_setting_value',
            }
        }

        query = {
            "source": self.source.pk,
            "view": 10,
            "name": "test layer",

            "table_fields": [field.pk, ],
            "table_export_fields": [field.pk, ],

            "filter_enable": True,
            "filter_fields": [filter_field, ]
        }

        response = self.client.patch(reverse('terralayer:layer-detail', args=[layer.pk, ]), query)

        self.assertEqual(response.status_code, HTTP_200_OK)

        response = response.json()
        self.assertEqual(1, len(response.get('filter_fields')))
        self.assertDictContainsSubset(filter_field, response.get('filter_fields')[0])
