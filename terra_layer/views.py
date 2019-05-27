from rest_framework.viewsets import ModelViewSet

from .models import Layer
from .serializers import LayerSerializer

class LayerViewset(ModelViewSet):
    model = Layer
    serializer_class = LayerSerializer
    authentication_classes = ()

    def get_queryset(self):
        return self.model.objects.all()
