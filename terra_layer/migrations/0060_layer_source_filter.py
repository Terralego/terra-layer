# Generated by Django 2.2.24 on 2021-09-28 13:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("terra_layer", "0059_auto_20210309_1510"),
    ]

    operations = [
        migrations.AddField(
            model_name="layer",
            name="source_filter",
            field=models.TextField(blank=True),
        ),
    ]
