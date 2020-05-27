import json
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from terra_layer.models import CustomStyle, FilterField, Layer

from django_geosource.models import PostGISSource, Field


UserModel = get_user_model()


class LayerDumpTestCase(TestCase):
    def setUp(self):
        self.source = PostGISSource.objects.create(
            name="test_view",
            db_name="test",
            db_password="test",
            db_host="localhost",
            geom_type=1,
            refresh=-1,
        )

    @mock.patch("sys.stdout", new_callable=StringIO)
    def test_command_launch_without_custom_style(self, mock_sdout):
        self.maxDiff = None
        layer = Layer.objects.create(
            source=self.source,
            name="Layer_without_custom_style",
            uuid="91c60192-9060-4bf6-b0de-818c5a362d89",
        )
        call_command("layer_dump", pk=layer.pk)
        self.assertEqual(
            json.loads(mock_sdout.getvalue()),
            {
                "fields": [],
                "custom_styles": [],
                "uuid": "91c60192-9060-4bf6-b0de-818c5a362d89",
                "name": "Layer_without_custom_style",
                "in_tree": True,
                "order": 0,
                "description": "",
                "layer_style": {},
                "layer_style_wizard": {},
                "settings": {},
                "active_by_default": False,
                "legends": [],
                "table_enable": False,
                "table_export_enable": False,
                "popup_enable": False,
                "popup_template": "",
                "popup_minzoom": 0.0,
                "popup_maxzoom": 22.0,
                "minisheet_enable": False,
                "minisheet_template": "",
                "highlight_color": "",
                "interactions": [],
                "source": "test_view",
                "group": None,
                "main_field": None,
                "view": None,
            },
        )

    def test_command_fail(self):
        with self.assertRaisesRegexp(CommandError, "Layer does not exist"):
            call_command("layer_dump", pk=999)

    @mock.patch("sys.stdout", new_callable=StringIO)
    def test_command_launch(self, mock_stdout):
        self.maxDiff = None
        layer = Layer.objects.create(
            source=self.source,
            name="Layer_with_custom_style",
            interactions=[
                {
                    "id": "terralego-eae-sync",
                    "interaction": "highlight",
                    "trigger": "mouseover",
                },
            ],
            minisheet_enable=True,
            popup_enable=True,
            highlight_color=True,
        )
        CustomStyle.objects.create(
            layer=layer,
            source=self.source,
            interactions=[
                {"id": "custom_style", "interaction": "highlight", "trigger": "click"},
            ],
        )
        call_command("layer_dump", pk=layer.pk)
        self.assertEqual(
            json.loads(mock_stdout.getvalue())["custom_styles"],
            [
                {
                    "style": {},
                    "interactions": [
                        {
                            "id": "custom_style",
                            "trigger": "click",
                            "interaction": "highlight",
                        }
                    ],
                    "source": "test_view",
                }
            ],
        )

    @mock.patch("sys.stdout", new_callable=StringIO)
    def test_command_launch_with_filer_field(self, mock_stdout):
        self.maxDiff = None
        field = Field.objects.create(source=self.source, name="tutu")

        layer = Layer.objects.create(
            source=self.source,
            name="Layer_with_custom_style",
            interactions=[
                {
                    "id": "terralego-eae-sync",
                    "interaction": "highlight",
                    "trigger": "mouseover",
                },
            ],
            minisheet_enable=True,
            popup_enable=True,
            highlight_color=True,
        )
        FilterField.objects.create(label="Test", field=field, layer=layer)
        call_command("layer_dump", pk=layer.pk)
        self.assertEqual(
            json.loads(mock_stdout.getvalue())["fields"],
            [
                {
                    "exportable": False,
                    "display": True,
                    "settings": {},
                    "field": "tutu",
                    "filter_enable": False,
                    "filter_settings": {},
                    "format_type": None,
                    "label": "Test",
                    "order": 0,
                    "shown": False,
                }
            ],
        )
