from hashlib import md5

from django.core.cache import cache
from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.utils.functional import cached_property
from django.utils.text import slugify
from django_geosource.models import Source, Field
from rest_framework.reverse import reverse

from .utils import get_layer_group_cache_key


class Scene(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    category = models.CharField(max_length=255, default="map")
    custom_icon = models.ImageField(
        max_length=255, upload_to="scene-icons", null=True, default=None
    )

    def get_absolute_url(self):
        return reverse("scene-detail", args=[self.pk])

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        return super().save(*args, **kwargs)


class LayerGroup(models.Model):
    view = models.ForeignKey(
        Scene, on_delete=models.CASCADE, related_name="layer_groups"
    )
    label = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self", null=True, on_delete=models.CASCADE, related_name="children"
    )
    order = models.IntegerField(default=0)
    exclusive = models.BooleanField(default=False)
    selectors = JSONField(null=True, default=None)
    settings = JSONField(default=dict)

    class Meta:
        unique_together = ["view", "label", "parent"]
        ordering = ["order"]


class Layer(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="layers")

    group = models.ForeignKey(
        LayerGroup, on_delete=models.CASCADE, null=True, related_name="layers"
    )
    name = models.CharField(max_length=255, blank=False)
    in_tree = models.BooleanField(default=True)

    order = models.IntegerField(default=0)

    description = models.TextField(blank=True)

    layer_style = JSONField(default=dict)
    settings = JSONField(default=dict)

    legends = JSONField(default=list)

    table_enable = models.BooleanField(default=False)
    table_export_enable = models.BooleanField(default=False)

    popup_enable = models.BooleanField(default=False)
    popup_template = models.TextField(blank=True)
    popup_minzoom = models.FloatField(default=0)
    popup_maxzoom = models.FloatField(default=22)

    minisheet_enable = models.BooleanField(default=False)
    minisheet_template = models.TextField(blank=True)

    highlight_color = models.CharField(max_length=255, blank=True)
    main_field = models.ForeignKey(
        Field, null=True, on_delete=models.CASCADE, related_name="is_main_of"
    )

    interactions = JSONField(default=list)

    fields = models.ManyToManyField(Field, through="FilterField")

    @property
    def style(self):
        return self.layer_style

    @cached_property
    def layer_identifier(self):
        return md5(f"{self.source.slug}-{self.pk}".encode("utf-8")).hexdigest()

    class Meta:
        ordering = ("order",)

    def save(self, **kwargs):
        super().save(**kwargs)

        # Invalidate cache for layer group
        if self.group:
            cache.delete(get_layer_group_cache_key(self.group.view))


class CustomStyle(models.Model):
    layer = models.ForeignKey(
        Layer, on_delete=models.CASCADE, related_name="custom_styles"
    )
    source = models.ForeignKey(
        Source, on_delete=models.CASCADE, related_name="sublayers"
    )
    style = JSONField(default=dict)
    interactions = JSONField(default=list)

    @property
    def layer_identifier(self):
        return md5(
            f"{self.source.slug}-{self.source.pk}-{self.pk}".encode("utf-8")
        ).hexdigest()


class FilterField(models.Model):
    field = models.ForeignKey(Field, on_delete=models.CASCADE)
    layer = models.ForeignKey(
        Layer, on_delete=models.CASCADE, related_name="fields_filters"
    )
    label = models.CharField(max_length=255, blank=True)

    order = models.IntegerField(default=0)

    filter_enable = models.BooleanField(default=False)
    filter_settings = JSONField(default=dict)
    format_type = models.CharField(max_length=255, default=None, null=True)

    exportable = models.BooleanField(default=False)
    shown = models.BooleanField(default=False)

    class Meta:
        ordering = ("order",)
