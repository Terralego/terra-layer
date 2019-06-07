
from rest_framework.serializers import ModelSerializer, PrimaryKeyRelatedField

from django.db import transaction

from django_geosource.models import Field
from django_geosource.serializers import FieldSerializer

from .models import Layer, FilterField


class FilterFieldSerializer(ModelSerializer):
    id = PrimaryKeyRelatedField(source='field', read_only=True)

    class Meta:
        model = FilterField
        exclude = ('layer', )


class LayerSerializer(ModelSerializer):
    fields = FilterFieldSerializer(many=True, read_only=True, source="fields_filters")

    @transaction.atomic
    def create(self, validated_data):
        instance = super().create(validated_data)

        # Update m2m through field
        self._update_m2m_through(instance, 'fields', FilterFieldSerializer)

        return instance

    @transaction.atomic
    def update(self, instance, validated_data):

        instance = super().update(instance, validated_data)

        # Update m2m through field
        self._update_m2m_through(instance, 'fields', FilterFieldSerializer)

        return instance

    def _update_m2m_through(self, instance, field, serializer):
        getattr(instance, field).clear()

        for value in self.initial_data.get(field, []):
            value['field'] = value['id']

            obj = serializer(data=value)
            if obj.is_valid(raise_exception=True):
                obj.save(layer=instance)

    class Meta:
        model = Layer
        fields = '__all__'
