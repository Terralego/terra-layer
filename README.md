# Terra Layer

This django applications aims to provide an API to connect django_geosource to django_geodata.
It serve an API that provides informations wanted by a frontend to configure data rendering.

## Set configuration

In Django settings, you must set the different views provided to fronted, like this:

```
TERRA_LAYER_VIEWS = {
    1: {
        'name': 'Human Name',
        'slug': 'slug-name',
    },
}
```

The dict key is the stored value in view field of layers.
