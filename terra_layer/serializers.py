from django.db import transaction
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from rest_framework.reverse import reverse
from rest_framework.serializers import (
    ModelSerializer,
    PrimaryKeyRelatedField,
    ValidationError,
)

from .models import CustomStyle, FilterField, Layer, Scene


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
            "order",
        )


class SceneDetailSerializer(ModelSerializer):
    slug = serializers.SlugField(required=False)
    icon = serializers.SerializerMethodField()

    def get_icon(self, obj):
        if obj.custom_icon:
            return obj.custom_icon.url

    class Meta:
        model = Scene
        fields = "__all__"


class FilterFieldSerializer(ModelSerializer):
    sourceFieldId = PrimaryKeyRelatedField(source="field", read_only=True)

    class Meta:
        model = FilterField
        exclude = ("layer", "order")


class CustomStyleSerializer(ModelSerializer):
    class Meta:
        model = CustomStyle
        exclude = ("layer",)


class LayerListSerializer(ModelSerializer):
    class Meta:
        model = Layer
        fields = ("id", "source", "group", "name", "order", "active_by_default")

    def to_representation(self, obj):
        return {
            **super().to_representation(obj),
            "view": obj.group.view.pk if obj.group else None,
        }


class LayerDetailSerializer(ModelSerializer):
    fields = FilterFieldSerializer(many=True, read_only=True, source="fields_filters")
    custom_styles = CustomStyleSerializer(many=True, read_only=True)

    @transaction.atomic
    def create(self, validated_data):
        instance = super().create(validated_data)

        # Update m2m through field
        self._update_nested(instance, "custom_styles", CustomStyleSerializer)
        self._update_m2m_through(instance, "fields", FilterFieldSerializer)

        return instance

    def to_representation(self, obj):
        return {
            **super().to_representation(obj),
            "view": obj.group.view.pk if obj.group else None,
        }

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

        for index, value in enumerate(self.initial_data.get(field, [])):
            try:
                value["field"] = value["id"]
            except KeyError:
                raise ValidationError("Fields must contain Source's field id")

            value["order"] = index  # Add order field

            obj = serializer(data=value)
            if obj.is_valid(raise_exception=True):
                obj.save(layer=instance)

    class Meta:
        model = Layer
        fields = "__all__"
