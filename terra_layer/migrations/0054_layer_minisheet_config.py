# Generated by Django 3.1.3 on 2020-11-24 10:36

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("terra_layer", "0053_auto_20201022_1000"),
    ]

    operations = [
        migrations.AddField(
            model_name="layer",
            name="minisheet_config",
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict),
        ),
    ]
