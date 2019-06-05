from enum import Enum
from django.db import models
from django.contrib.postgres.fields import JSONField

from django_geosource.models import Source, Field


class Layer(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE)

    view = models.IntegerField()
    name = models.CharField(max_length=255, blank=False)

    order = models.IntegerField(default=0)

    description = models.TextField(blank=True)

    layer_style = models.TextField(blank=True)

    legend_enable = models.BooleanField(default=False)
    legend_template = models.TextField(blank=True)

    table_enable = models.BooleanField(default=False)
    table_export_enable = models.BooleanField(default=False)
    table_fields = models.ManyToManyField(Field, related_name='in_layers')
    table_export_fields = models.ManyToManyField(Field, related_name='in_layers_export')

    popup_enable = models.BooleanField(default=False)
    popup_template = models.TextField(blank=True)

    minisheet_enable = models.BooleanField(default=False)
    minisheet_template = models.TextField(blank=True)

    filter_enable = models.BooleanField(default=False)
    filter_fields = models.ManyToManyField(Field, through="FilterField")


class FilterField(models.Model):
    field = models.ForeignKey(Field, on_delete=models.CASCADE)
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, related_name="fields_filters")
    filter_type = models.IntegerField(default=0)
    filter_settings = JSONField(default={})
