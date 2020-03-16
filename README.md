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
# Map settings. Sent to mapbox clientside.
TERRA_DEFAULT_MAP_SETTINGS = {
    'accessToken': '<your mapbox access token>',
    'backgroundStyle': '<background style file>',
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

# Style and Legend autogeneration
TERRA_LAYER_STYLE_SETTINGS = {
    "circle_min_legend_height": 14, # minimum height for circle legend label.
    "fill_color": "#0000cc", # Default fill color
    "fill_opacity": 0.4, # Default fill opacity
    "stroke_color": "#ffffff", # Default stroke color
    "stroke_width": 0.3, # Default stroke width
}
```

## Add a load xls command

You can define in the project using _terra_layer_ a load_xls command that takes
two parameters:

- -s (--scene-name): receive the scene name.
- -f (--file): the input xls file to load.

This command is launched when a file is send with a view. See the test project
for an exemple.

## To start a dev instance

Define settings you wants in `test_terralayer` django project.

```sh
docker-compose up
```

First start should failed as the database need to be initialized. Just launch
the same command twice.

Then initialize the database:

```sh
docker-compose run --rm web /code/venv/bin/python3 /code/src/manage.py migrate
```

You can now edit your code. A django runserver is launched internally so the
this is an autoreload server.

You can access to the api on http://localhost:8000/api/

## Test

To run test suite, just launch:

```sh
docker-compose run --rm web /code/venv/bin/python3 /code/src/manage.py test
```

## Contributing

You must use factoryboy factories to develop your tests. The factories are available
at `terra_layer/tests/factories`

You must update the CHANGES.md file on each MR and increment version if needed.
