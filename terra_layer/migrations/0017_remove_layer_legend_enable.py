# Generated by Django 2.0.13 on 2019-06-26 07:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('terra_layer', '0016_auto_20190625_1436'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='layer',
            name='legend_enable',
        ),
    ]