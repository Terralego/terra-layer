from rest_framework.serializers import (
    ModelSerializer,
    PrimaryKeyRelatedField,
    ValidationError,
)

from django.db import transaction

from .models import Layer, LayerGroup, FilterField, CustomStyle


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
            "view": obj.group.view,
        }

    def _get_layer_group(self, data):
        view = data["view"]

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
