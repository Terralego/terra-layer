# Generated by Django 2.0.13 on 2019-06-26 07:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("terra_layer", "0017_remove_layer_legend_enable")]

    operations = [
        migrations.RenameField(
            model_name="layer", old_name="legend_template", new_name="legends"
        )
    ]
