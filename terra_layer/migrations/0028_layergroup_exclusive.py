# Generated by Django 2.1.9 on 2019-07-16 10:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('terra_layer', '0027_auto_20190715_1631'),
    ]

    operations = [
        migrations.AddField(
            model_name='layergroup',
            name='exclusive',
            field=models.BooleanField(default=False),
        ),
    ]