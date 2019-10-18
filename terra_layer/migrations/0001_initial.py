# Generated by Django 2.0.13 on 2019-05-22 15:22

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [("django_geosource", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="FilterField",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("filter_type", models.IntegerField()),
                (
                    "filter_settings",
                    django.contrib.postgres.fields.jsonb.JSONField(default={}),
                ),
                (
                    "field",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="django_geosource.Field",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Layer",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("view", models.IntegerField()),
                ("name", models.CharField(max_length=255)),
                ("order", models.IntegerField(default=0)),
                ("description", models.TextField(blank=True)),
                ("layer_style", models.TextField(blank=True)),
                ("legend_enable", models.BooleanField(default=False)),
                ("legend_template", models.TextField(blank=True)),
                ("table_enable", models.BooleanField(default=False)),
                ("table_export_enable", models.BooleanField(default=False)),
                ("popup_enable", models.BooleanField(default=False)),
                ("popup_template", models.TextField(blank=True)),
                ("minisheet_enable", models.BooleanField(default=False)),
                ("minisheet_template", models.TextField(blank=True)),
                ("filter_enable", models.BooleanField(default=False)),
                (
                    "filter_fields",
                    models.ManyToManyField(
                        through="terra_layer.FilterField", to="django_geosource.Field"
                    ),
                ),
                (
                    "source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="django_geosource.Source",
                    ),
                ),
                (
                    "table_export_fields",
                    models.ManyToManyField(
                        related_name="in_layers_export", to="django_geosource.Field"
                    ),
                ),
                (
                    "table_fields",
                    models.ManyToManyField(
                        related_name="in_layers", to="django_geosource.Field"
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="filterfield",
            name="layer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="terra_layer.Layer"
            ),
        ),
    ]
