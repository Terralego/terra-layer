import argparse
from django.core.management.base import BaseCommand, CommandError
from terra_layer.models import Layer, Scene
from terra_layer.serializers import LayerDetailSerializer
from django_geosource.models import Source
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
            field["field"] = source.fields.get(name=field["field"]).pk

        parts = data["name"].split("/")
        layer_name = parts.pop()

        # Try to find already existing layer
        try:
            layer = Layer.objects.get(uuid=data["uuid"])
            exists = True
        except Exception:
            layer = Layer()
            exists = False

        del data["group"]  # Remove group as we compute it later
        data["name"] = layer_name

        layer_detail_serializer = LayerDetailSerializer(instance=layer, data=data)
        try:
            layer_detail_serializer.is_valid(raise_exception=True)
        except Exception as e:
            raise CommandError(f"A validation error occurred with data: {e}")

        layer_detail_serializer.save()

        # Here we insert layer in tree if not previously existing
        if not exists:

            # Add the layer in scene tree
            # Here we assume that missing groups are added at first position of current node
            # We create missing group with default exclusive group configuration (should be corrected later if necessary)
            scene = Scene.objects.get(id=data["view"])
            current_node = scene.tree
            for part in parts:
                found = False
                for group in current_node:
                    if group.get("group") and group["label"] == part:
                        current_node = group["children"]
                        found = True
                        break
                if not found:
                    # Add the missing group
                    new_group = {"group": True, "label": part, "children": []}
                    current_node.insert(0, new_group)
                    current_node = new_group["children"]

            # Node if found (or created) we can add the geolayer now
            current_node.append(
                {
                    "geolayer": layer_detail_serializer.instance.id,
                    "label": layer_detail_serializer.instance.name,
                }
            )
            scene.save()
