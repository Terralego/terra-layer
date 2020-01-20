# Generated by Django 2.1.9 on 2019-07-16 14:43

import django.contrib.postgres.fields.jsonb
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("terra_layer", "0028_layergroup_exclusive")]

    operations = [
        migrations.AddField(
            model_name="layergroup",
            name="selectors",
            field=django.contrib.postgres.fields.jsonb.JSONField(default=list),
        ),
        migrations.AlterField(
            model_name="layer",
            name="group",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="layers",
                to="terra_layer.LayerGroup",
            ),
        ),
    ]
