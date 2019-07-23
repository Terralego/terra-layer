# Generated by Django 2.1.9 on 2019-07-23 12:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('terra_layer', '0034_layer_in_tree'),
    ]

    operations = [
        migrations.AlterField(
            model_name='layer',
            name='popup_maxzoom',
            field=models.FloatField(default=22),
        ),
        migrations.AlterField(
            model_name='layer',
            name='popup_minzoom',
            field=models.FloatField(default=0),
        ),
    ]