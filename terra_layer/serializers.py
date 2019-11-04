from django.db import transaction
from rest_framework.serializers import (
    ModelSerializer,
    PrimaryKeyRelatedField,
    ValidationError,
)
from rest_framework.fields import SerializerMethodField
from rest_framework.reverse import reverse
from rest_framework import serializers

from .models import CustomStyle, FilterField, Layer, LayerGroup, Scene


class SceneListSerializer(ModelSerializer):
    url = serializers.CharField(source="get_absolute_url", read_only=True)
    layers_tree_url = SerializerMethodField()

    def get_layers_tree_url(self, obj):
        return reverse("layerview", args=[obj.slug])

    class Meta:
        model = Scene
        fields = (
            "id",
            "name",
            "slug",
            "category",
            "custom_icon",
            "url",
            "layers_tree_url",
        )


class SceneDetailSerializer(ModelSerializer):
    icon = serializers.SerializerMethodField()

    def get_icon(self, obj):
        if obj.custom_icon:
            return obj.custom_icon.url

    class Meta:
        model = Scene
        fields = "__all__"


class FilterFieldSerializer(ModelSerializer):
    id = PrimaryKeyRelatedField(source="field", read_only=True)

    class Meta:
        model = FilterField
        exclude = ("layer",)


class CustomStyleSerializer(ModelSerializer):
    class Meta:
        model = CustomStyle
        exclude = ("layer",)


class LayerSerializer(ModelSerializer):
    fields = FilterFieldSerializer(many=True, read_only=True, source="fields_filters")
    custom_styles = CustomStyleSerializer(many=True, read_only=True)

    @transaction.atomic
    def create(self, validated_data):
        instance = super().create(validated_data)

        # Update m2m through field
        self._update_nested(instance, "custom_styles", CustomStyleSerializer)
        self._update_m2m_through(instance, "fields", FilterFieldSerializer)

        return instance

    def to_internal_value(self, data):
        data["group"], data["name"] = self._get_layer_group(data)
        return super().to_internal_value(data)

    def to_representation(self, obj):
        return {
            **super().to_representation(obj),
            "name": self._get_name_path(obj),
            "view": obj.group.view.pk,
        }

    def _get_layer_group(self, data):
        try:
            view = Scene.objects.get(pk=data["view"])
        except (Scene.DoesNotExist, KeyError):
            raise ValidationError("Scene does not exist")

        try:
            group_path, layer_name = data["name"].rsplit("/", 1)
        except ValueError:
            group_path, layer_name = "Unknown", data["name"]

        group = None
        for group_name in group_path.split("/"):
            if group:
                group, _ = group.children.get_or_create(label=group_name)
            else:
                group, _ = LayerGroup.objects.get_or_create(view=view, label=group_name)

        return group.pk, layer_name

    def _get_name_path(self, obj):
        def get_group_path(group):
            name = group.label
            if group.parent:
                name = get_group_path(group.parent) + f"/{name}"
            return name

        group_path = get_group_path(obj.group)
        return f"{group_path}/{obj.name}"

    @transaction.atomic
    def update(self, instance, validated_data):

        instance = super().update(instance, validated_data)

        # Update m2m through field
        self._update_m2m_through(instance, "fields", FilterFieldSerializer)
        self._update_nested(instance, "custom_styles", CustomStyleSerializer)

        return instance

    def _update_nested(self, instance, field, serializer):
        getattr(instance, field).all().delete()

        for value in self.initial_data.get(field, []):
            obj = serializer(data=value)
            if obj.is_valid(raise_exception=True):
                obj.save(layer=instance)

    def _update_m2m_through(self, instance, field, serializer):
        getattr(instance, field).clear()

        for value in self.initial_data.get(field, []):
            try:
                value["field"] = value["id"]
            except KeyError:
                raise ValidationError("Fields must contain Source's field id")

            obj = serializer(data=value)
            if obj.is_valid(raise_exception=True):
                obj.save(layer=instance)

    class Meta:
        model = Layer
        fields = "__all__"
