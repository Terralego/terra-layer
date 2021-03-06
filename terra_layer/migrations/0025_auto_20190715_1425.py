# Generated by Django 2.1.9 on 2019-07-15 12:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [("terra_layer", "0025_layer_settings")]

    operations = [
        migrations.CreateModel(
            name="LayerGroup",
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
                ("label", models.CharField(max_length=255)),
                (
                    "parent",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="terra_layer.LayerGroup",
                    ),
                ),
            ],
        ),
        migrations.AlterUniqueTogether(
            name="layergroup", unique_together={("view", "label")}
        ),
    ]
