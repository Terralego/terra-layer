# Generated by Django 2.1.9 on 2019-07-23 11:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('terra_layer', '0033_layergroup_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='layer',
            name='in_tree',
            field=models.BooleanField(default=True),
        ),
    ]
