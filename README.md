[![Build Status](https://travis-ci.org/Terralego/terra-layer.svg?branch=master)](https://travis-ci.org/Terralego/terra-layer)
[![codecov](https://codecov.io/gh/Terralego/terra-layer/branch/master/graph/badge.svg)](https://codecov.io/gh/Terralego/terra-layer)
[![PyPi version](https://pypip.in/v/terra-layer/badge.png)](https://pypi.org/project/terra-layer/)

# Terra Layer

This django applications aims to provide an API to connect django_geosource to django_geodata.
It serve an API that provides informations wanted by a frontend to configure data rendering.

## Pre-requisite

You need the last version of docker and docker-compose to execute a dev instance.

## Set configuration

In Django settings, you must set the different views provided to fronted, like this:

```python
TERRA_DEFAULT_MAP_SETTINGS = {
    "accessToken": "<your mapbox access token>",
    "backgroundStyle": "<background style file>",
    'center': [-0.655, 43.141], # Default view center
    'zoom': 7.7, # Default zoom
    'maxZoom': 19.9,
    'minZoom': 5,
    'fitBounds': { # Default bounding box
        'coordinates': [
            [-4.850, 46.776],
            [-0.551, 48.886]
        ],
    },
}
```

## To start a dev instance

Define settings you wants in `test_terralayer` django project.

```sh
docker-compose up
```

First start should failed as the database need to be initialized. Just launch
the same command twice.

Then initialize the database:

```sh
docker-compose run web /code/venv/bin/python3 /code/src/manage.py migrate
```

You can now edit your code. A django runserver is launched internally so the 
this is an autoreload server.

You can access to the api on http://localhost:8000/api/

## Test

To run test suite, just launch:

```sh
docker-compose run web /code/venv/bin/python3 /code/src/manage.py test
```

## Contributing

You must use factoryboy factories to develop your tests. The factories are available 
at `terra_layer/tests/factories`

You must update the CHANGES.md file on each MR and increment version if needed.
