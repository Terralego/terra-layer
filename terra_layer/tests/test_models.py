from django.test import TestCase

from terra_layer.models import Layer

from django_geosource.models import PostGISSource


class LayerTestCase(TestCase):
    def test_str(self):
        source = PostGISSource.objects.create(
            name="test",
            db_name="test",
            db_password="test",
            db_host="localhost",
            geom_type=1,
            refresh=-1,
        )
        layer = Layer.objects.create(
            source=source, name=f"foo", uuid="91c60192-9060-4bf6-b0de-818c5a362d89",
        )
        self.assertEqual(str(layer), "Layer({}) - foo".format(layer.pk))
