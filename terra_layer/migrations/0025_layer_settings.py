# Generated by Django 2.0.13 on 2019-08-20 09:36

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('terra_layer', '0024_customstyle_interactions'),
    ]

    operations = [
        migrations.AddField(
            model_name='layer',
            name='settings',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict),
        ),
    ]