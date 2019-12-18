import factory

from ..models import Scene, Layer


class SceneFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Scene

    custom_icon = factory.django.ImageField()


class LayerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Layer
