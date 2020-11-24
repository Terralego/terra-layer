# Generated by Django 3.1.3 on 2020-11-24 10:36

from django.db import migrations


def populate_minisheet_config(apps, schema_editor):
    LayerModel = apps.get_model("terra_layer", "Layer")
    for layer in LayerModel.objects.all():
        layer.minisheet_config = {
            "enable": layer.minisheet_enable,
            "template": layer.minisheet_template,
            "highlight_color": layer.highlight_color,
            "advanced": True,
            "wizard": {},
        }
        layer.save()


class Migration(migrations.Migration):

    dependencies = [
        ("terra_layer", "0054_layer_minisheet_config"),
    ]

    operations = [
        migrations.RunPython(
            populate_minisheet_config,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
