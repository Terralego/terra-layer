# Generated by Django 3.1.3 on 2020-11-24 10:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("terra_layer", "0055_auto_20201124_1036"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="layer",
            name="highlight_color",
        ),
        migrations.RemoveField(
            model_name="layer",
            name="minisheet_enable",
        ),
        migrations.RemoveField(
            model_name="layer",
            name="minisheet_template",
        ),
    ]
