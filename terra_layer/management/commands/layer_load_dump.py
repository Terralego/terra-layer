import argparse
from django.core.management.base import BaseCommand, CommandError
from terra_layer.models import Layer, Scene, LayerGroup
from terra_layer.serializers import LayerSerializer
from django_geosource.models import Field, Source
import json


class Command(BaseCommand):
    help = "Load a dumped layer"

    def add_arguments(self, parser):
        parser.add_argument(
            "-file",
            type=argparse.FileType("r"),
            required=True,
            action="store",
            help="json file path",
        )

    def handle(self, *args, **options):
        data = json.load(options["file"])

        source = Source.objects.get(slug=data["source"])

        fk_fields = (
            (Scene, "view", "slug"),
            (Source, "source", "slug"),
        )

        for klass, field, sfield in fk_fields:
            if data.get(field):
                data[field] = klass.objects.get(**{sfield: data[field]}).pk

        for cs in data["custom_styles"]:
            cs["source"] = Source.objects.get(slug=cs["source"]).pk

        if data.get("main_field"):
            data["main_field"] = source.fields.get(name=data["main_field"]).pk

        for field in data["fields"]:
            try:
                field["id"] = source.fields.get(name=field["field"]).pk
            except Field.DoesNotExist:
                raise

        # Try to find already existing layer
        try:
            _, layer_name = data["name"].rsplit("/", 1)
            group = LayerGroup.objects.get(view=data["view"], label=data["group"])
            layer = Layer.objects.get(group=group, name=layer_name)
        except Exception:
            layer = Layer()

        srlz = LayerSerializer(instance=layer, data=data)
        try:
            srlz.is_valid(raise_exception=True)
        except Exception as e:
            raise CommandError(f"A validation error occured with data: {e}")

        srlz.save()
