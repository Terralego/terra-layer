from geostore.models import Layer, LayerGroup


def layer_callback(geosource):
    group_name = geosource.settings.pop("group", "reference")
    layer, _ = Layer.objects.get_or_create(
        name=geosource.slug, defaults={"settings": geosource.settings,}
    )

    if not layer.layer_groups.filter(name=group_name).exists():
        group, _ = LayerGroup.objects.get_or_create(name=group_name)
        group.layers.add(layer)

    return layer
