from rest_framework.serializers import ModelSerializer

from django_geosource.models import Field
from django_geosource.serializers import FieldSerializer

from .models import Layer, FilterField


class FilterFieldSerializer(ModelSerializer):

    class Meta:
        model = FilterField
        exclude = ('layer', )


class LayerSerializer(ModelSerializer):
    table_fields = FieldSerializer(many=True, read_only=True)
    table_export_fields = FieldSerializer(many=True, read_only=True)
    filter_fields = FilterFieldSerializer(many=True, read_only=True, source="fields_filters")

    m2m_fields = {
        'table_fields': Field,
        'table_export_fields': Field,
    }

    def create(self, validated_data):
        instance = super().create(validated_data)

        # Update simple m2m models
        for field, model in self.m2m_fields.items():
            self._update_m2m(instance, field, model)

        # Update m2m through field
        self._update_m2m_through(instance, 'filter_fields', FilterFieldSerializer)

        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)

        # Update simple m2m models
        for field, model in self.m2m_fields.items():
            self._update_m2m(instance, field, model)

        # Update m2m through field
        self._update_m2m_through(instance, 'filter_fields', FilterFieldSerializer)

        return instance

    def _update_m2m_through(self, instance, field, serializer):
        getattr(instance, field).clear()

        for value in self.initial_data.get(field, []):
            obj = serializer(data=value)
            if obj.is_valid(raise_exception=True):
                obj.save(layer=instance)

    def _update_m2m(self, instance, field, model):
        instance_field = getattr(instance, field)

        instance_field.clear()

        for value in self.initial_data.get(field, []):
            instance_field.add(model.objects.get(pk=value))

    class Meta:
        model = Layer
        fields = '__all__'
