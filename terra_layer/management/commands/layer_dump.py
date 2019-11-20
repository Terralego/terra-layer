from django.core.management.base import BaseCommand, CommandError
from terra_layer.models import Layer, LayerGroup, Scene
from terra_layer.serializers import LayerSerializer
from django_geosource.models import Field, Source
import json


class Command(BaseCommand):
    help = "Dump a layer to json format"

    def add_arguments(self, parser):
        parser.add_argument(
            "-pk", type=int, action="store", help="Pk of the layer to export"
        )

    def handle(self, *args, **options):
        try:
            self.layer = Layer.objects.get(pk=options.get("pk"))
        except Layer.DoesNotExist:
            raise CommandError("Layer does not exist")

        serialized = LayerSerializer(self.layer).data
        self.clean_ids(serialized)

        self.stdout.write(json.dumps(serialized))

    def clean_ids(self, serialized):
        excluded_fields = ("id",)
        for field in excluded_fields:
            serialized.pop(field)

        # Clean custom_style id
        [cs.pop("id") for cs in serialized["custom_styles"]]

        for field in serialized["fields"]:
            field.pop("id")
            field["field"] = Field.objects.get(pk=field["field"]).name

        fk_fields = (
            (LayerGroup, "group", "label"),
            (Scene, "view", "slug"),
            (Source, "source", "slug"),
            (Field, "main_field", "name"),
        )

        for klass, field, sfield in fk_fields:
            serialized[field] = getattr(
                klass.objects.get(pk=serialized.get(field)), sfield
            )
