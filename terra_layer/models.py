from hashlib import md5
from enum import Enum
from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.utils.functional import cached_property

from django_geosource.models import Source, Field

VIEW_CHOICES = [(view['pk'], view['name']) for slug, view in settings.TERRA_LAYER_VIEWS.items()]


class LayerGroup(models.Model):
    view = models.IntegerField()
    label = models.CharField(max_length=255)
    parent = models.ForeignKey('self', null=True, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)
    exclusive = models.BooleanField(default=False)
    selectors = JSONField(null=True, default=None)

    class Meta:
        unique_together = ['view', 'label']
        ordering = ['order']


class Layer(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='layers')

    group = models.ForeignKey(LayerGroup, on_delete=models.CASCADE, null=True, related_name="layers")
    name = models.CharField(max_length=255, blank=False)

    order = models.IntegerField(default=0)

    description = models.TextField(blank=True)

    layer_style = JSONField(default=dict)
    settings = JSONField(default=dict)

    legends = JSONField(default=list)

    table_enable = models.BooleanField(default=False)
    table_export_enable = models.BooleanField(default=False)

    popup_enable = models.BooleanField(default=False)
    popup_template = models.TextField(blank=True)
    popup_minzoom = models.FloatField(default=10)
    popup_maxzoom = models.FloatField(default=10)

    minisheet_enable = models.BooleanField(default=False)
    minisheet_template = models.TextField(blank=True)

    interactions = JSONField(default=list)

    fields = models.ManyToManyField(Field, through="FilterField")

    @property
    def style(self):
        return self.layer_style

    @cached_property
    def layer_identifier(self):
        return md5(f"{self.source.slug}-{self.pk}".encode('utf-8')).hexdigest()

    class Meta:
        permissions = (
            ('can_manage_layers', 'Can manage layers'),
        )


class CustomStyle(models.Model):
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, related_name='custom_styles')
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='sublayers')
    style = JSONField(default=dict)
    interactions = JSONField(default=list)

    @property
    def layer_identifier(self):
        return md5(f"{self.source.slug}-{self.source.pk}-{self.pk}".encode('utf-8')).hexdigest()


class FilterField(models.Model):
    field = models.ForeignKey(Field, on_delete=models.CASCADE)
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, related_name="fields_filters")
    label = models.CharField(max_length=255, blank=True)

    filter_enable = models.BooleanField(default=False)
    filter_settings = JSONField(default=dict)

    exportable = models.BooleanField(default=False)
    shown = models.BooleanField(default=False)
