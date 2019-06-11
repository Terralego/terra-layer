from hashlib import md5
from enum import Enum
from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.utils.functional import cached_property

from django_geosource.models import Source, Field

VIEW_CHOICES = [(key, view['name']) for key, view in settings.TERRA_LAYER_VIEWS.items()]

class Layer(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE)

    view = models.IntegerField(choices=VIEW_CHOICES)
    name = models.CharField(max_length=255, blank=False)

    order = models.IntegerField(default=0)

    description = models.TextField(blank=True)

    layer_style = JSONField(default=dict)

    legend_enable = models.BooleanField(default=False)
    legend_template = models.TextField(blank=True)

    table_enable = models.BooleanField(default=False)
    table_export_enable = models.BooleanField(default=False)

    popup_enable = models.BooleanField(default=False)
    popup_template = models.TextField(blank=True)
    popup_minzoom = models.FloatField(default=10)
    popup_maxzoom = models.FloatField(default=10)

    minisheet_enable = models.BooleanField(default=False)
    minisheet_template = models.TextField(blank=True)

    filter_enable = models.BooleanField(default=False)
    fields = models.ManyToManyField(Field, through="FilterField")

    @cached_property
    def layer_id(self):
        return md5(self.name.encode('utf-8')).hexdigest()

    class Meta:
        permissions = (
            ('can_manage_layers', 'Can manage layers'),
        )


class FilterField(models.Model):
    field = models.ForeignKey(Field, on_delete=models.CASCADE)
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, related_name="fields_filters")
    filter_type = models.IntegerField(default=0)
    filter_settings = JSONField(default={})

    exportable = models.BooleanField(default=False)
    shown = models.BooleanField(default=False)
