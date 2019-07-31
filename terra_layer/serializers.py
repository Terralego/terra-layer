from rest_framework.serializers import ModelSerializer, PrimaryKeyRelatedField, ValidationError

from django.db import transaction

from .models import Layer, FilterField, CustomStyle


class FilterFieldSerializer(ModelSerializer):
    id = PrimaryKeyRelatedField(source='field', read_only=True)

    class Meta:
        model = FilterField
        exclude = ('layer', )


class CustomStyleSerializer(ModelSerializer):

    class Meta:
        model = CustomStyle
        exclude = ('layer', )


class LayerSerializer(ModelSerializer):
    fields = FilterFieldSerializer(many=True, read_only=True, source="fields_filters")
    custom_styles = CustomStyleSerializer(many=True, read_only=True)

    @transaction.atomic
    def create(self, validated_data):
        instance = super().create(validated_data)

        # Update m2m through field
        self._update_nested(instance, 'custom_styles', CustomStyleSerializer)
        self._update_m2m_through(instance, 'fields', FilterFieldSerializer)

        return instance

    @transaction.atomic
    def update(self, instance, validated_data):

        instance = super().update(instance, validated_data)

        # Update m2m through field
        self._update_m2m_through(instance, 'fields', FilterFieldSerializer)
        self._update_nested(instance, 'custom_styles', CustomStyleSerializer)

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
                value['field'] = value['id']
            except KeyError:
                raise ValidationError("Fields must contain Source's field id")

            obj = serializer(data=value)
            if obj.is_valid(raise_exception=True):
                obj.save(layer=instance)

    class Meta:
        model = Layer
        fields = '__all__'
