# Generated by Django 2.0.13 on 2019-06-12 15:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("terra_layer", "0009_auto_20190612_1020")]

    operations = [
        migrations.AlterField(
            model_name="filterfield",
            name="filter_type",
            field=models.CharField(max_length=255, null=True),
        )
    ]
