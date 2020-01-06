from hashlib import md5
import uuid

from django.core.cache import cache
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.utils.functional import cached_property
from django.utils.text import slugify
from django_geosource.models import Source, Field
from rest_framework.reverse import reverse

from .utils import get_layer_group_cache_key
from .schema import JSONSchemaValidator, SCENE_LAYERTREE


class Scene(models.Model):
    """ A scene is a group of data visualisation in terra-visu.
    It's also a main menu entry.
    """

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    category = models.CharField(max_length=255, default="map")
    custom_icon = models.ImageField(
        max_length=255, upload_to="scene-icons", null=True, default=None
    )
    order = models.IntegerField(default=0, db_index=True)
    tree = JSONField(
        default=list, validators=[JSONSchemaValidator(limit_value=SCENE_LAYERTREE)]
    )

    def get_absolute_url(self):
        return reverse("scene-detail", args=[self.pk])

    def tree2models(self, current_node=None, parent=None, order=0):
        """
        Generate groups structure from admin layer tree.
        This is a recursive function to handle each step of process.

        :param current_node: current node of the tree
        :param parent: The parent group of current node
        :param order: Current order to keep initial json order
        :returns: Nothing
        """

        # Init case, we've just launch the process
        if current_node is None:
            current_node = self.tree
            self.layer_groups.all().delete()  # Clear all groups to generate brand new one

        if not parent:
            # Create a default unique parent group that is ignored at export
            parent = LayerGroup.objects.create(view=self, label="Root")

        if isinstance(current_node, list):
            for idx, child in enumerate(current_node):
                self.tree2models(current_node=child, parent=parent, order=idx)

        elif "group" in current_node:
            # Handle groups
            group = parent.children.create(
                view=self,
                label=current_node["label"],
                exclusive=current_node.get("exclusive", False),
                selectors=current_node.get("selectors"),
                settings=current_node.get("settings", {}),
                order=order,
            )

            if "children" in current_node:
                self.tree2models(current_node=current_node["children"], parent=group)

        elif "geolayer" in current_node:
            # Handle layers
            layer = Layer.objects.get(pk=current_node["geolayer"])
            layer.group = parent
            layer.order = order
            layer.save()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)
        self.tree2models()  # Generate LayerGroups according to the tree

    class Meta:
        ordering = ["order"]


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
        ordering = ["order"]


class Layer(models.Model):
    uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="layers")

    group = models.ForeignKey(
        LayerGroup, on_delete=models.SET_NULL, null=True, related_name="layers"
    )
    name = models.CharField(max_length=255, blank=False)
    in_tree = models.BooleanField(default=True)

    order = models.IntegerField(default=0)

    description = models.TextField(blank=True)

    layer_style = JSONField(default=dict)
    settings = JSONField(default=dict)
    active_by_default = models.BooleanField(default=False)

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
        ordering = ("order", "name")

    def save(self, **kwargs):
        super().save(**kwargs)

        # Invalidate cache for layer group
        if self.group:
            cache.delete(get_layer_group_cache_key(self.group.view))

    def __str__(self):
        return f"Layer({self.id}) - {self.name}"


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
