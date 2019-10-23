import factory

from ..models import Scene


class SceneFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Scene

    custom_icon = factory.django.ImageField()
