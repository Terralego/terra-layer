from django.contrib.gis.geos import Point
from django.test import TestCase

from terra_layer.models import Layer

from django_geosource.models import PostGISSource
from geostore.models import Feature

from terra_layer import style

import random


class StyleTestCase(TestCase):
    def setUp(self):
        self.source = PostGISSource.objects.create(
            name="test",
            db_name="test",
            db_password="test",
            db_host="localhost",
            geom_type=1,
            refresh=-1,
        )
        self.layer = Layer.objects.create(
            source=self.source, name="foo", uuid="91c60192-9060-4bf6-b0de-818c5a362d89",
        )

    def _feature_factory(self, geo_layer, **properties):
        return Feature.objects.create(
            layer=geo_layer,
            geom=Point(-1.560408, 47.218658),
            properties=properties,
        )

    def test_min_max(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=2),

        self.assertEqual(style.min_max(geo_layer, 'a'), [1.0, 2.0])

    def test_empty(self):
        geo_layer = self.source.get_layer()
        geo_layer.layer_style_wizard = {}
        geo_layer.save()

        # Make a random change on the layer before save
        self.layer.name = 'foobar'
        self.layer.save()
        self.assertEqual(self.layer.layer_style, {})

    def test_1feature(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),

        self.layer.layer_style_wizard = {}
        self.layer.save()

        self.assertEqual(self.layer.layer_style, {})

    graduated_fail = {
        'type': 'fill',
        'paint': {
            'fill-color': [
                'step',
                ['get', 'a'],
                '#aa0000',
                1, '#770000',
                2, '#330000',
                3, '#000000'
            ],
            'fill-outline-color': '#ffffff'
        }
    }

    def test_0graduated(self):
        self.layer.layer_style_wizard = {
            "property": "a",
            "symbology": "graduated",
            "method": "equal_interval",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, self.graduated_fail)

    def test_2equal_interval(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=2),

        self.layer.layer_style_wizard = {
            "property": "a",
            "symbology": "graduated",
            "method": "equal_interval",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, {
            'type': 'fill',
            'paint': {
                'fill-color': [
                    'step',
                    ['get', 'a'],
                    '#aa0000',
                    1.25, '#770000',
                    1.5, '#330000',
                    1.75, '#000000'
                ],
                'fill-outline-color': '#ffffff'
            }
        })
        self.assertEqual(self.layer.legends, [{
            'color': '#aa0000',
            'label': '[1.0 – 1.25)',
            'shape': 'square'
        }, {
            'color': '#770000',
            'label': '[1.25 – 1.5)',
            'shape': 'square'
        }, {
            'color': '#330000',
            'label': '[1.5 – 1.75)',
            'shape': 'square'
        }, {
            'color': '#000000',
            'label': '[1.75 – 2.0]',
            'shape': 'square'
        }])

    def test_2jenks(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=2),

        self.layer.layer_style_wizard = {
            "property": "a",
            "symbology": "graduated",
            "method": "jenks",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, {
            'type': 'fill',
            'paint': {
                'fill-color': [
                    'step',
                    ['get', 'a'],
                    '#aa0000',
                    2.0, '#770000',
                    2.0, '#330000',
                ],
                'fill-outline-color': '#ffffff'
            }
        })
        self.assertEqual(self.layer.legends, [{
            'color': '#aa0000',
            'label': '[1.0 – 2.0)',
            'shape': 'square'
        }, {
            'color': '#770000',
            'label': '[2.0 – 2.0]',
            'shape': 'square'
        }])

    def test_2quantile(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=2),

        self.layer.layer_style_wizard = {
            "property": "a",
            "symbology": "graduated",
            "method": "quantile",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, {
            'type': 'fill',
            'paint': {
                'fill-color': [
                    'step',
                    ['get', 'a'],
                    '#aa0000',
                    2, '#770000',
                    2, '#330000'
                ],
                'fill-outline-color': '#ffffff'
            }
        })
        self.assertEqual(self.layer.legends, [{
            'color': '#aa0000',
            'label': '[1.0 – 2.0)',
            'shape': 'square'
        }, {
            'color': '#770000',
            'label': '[2.0 – 2.0]',
            'shape': 'square'
        }])

    def test_2circle(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=2),

        self.layer.layer_style_wizard = {
            "property": "a",
            "symbology": "circle",
            "max_diameter": 200,
            "fill_color": "#0000cc",
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, {
            'type': 'circle',
            'paint': {
                'circle-radius': [
                    'interpolate', 'linear',
                    ['get', 'a'],
                    0, 0,
                    2.0, 200
                ],
                'circle-stroke-color': '#ffffff',
            }
        })
        self.assertEqual(self.layer.legends, [{
            'radius': 0,
            'label': '0',
            'shape': 'circle'
        }, {
            'radius': 200,
            'label': '2.0',
            'shape': 'circle'
        }])

    def test_equal_interval_gauss(self):
        geo_layer = self.source.get_layer()

        random.seed(33)
        for index in range(0, 1000):
            self._feature_factory(geo_layer, a=random.gauss(0, 5)),

        self.layer.layer_style_wizard = {
            "property": "a",
            "symbology": "graduated",
            "method": "equal_interval",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, {
            'type': 'fill',
            'paint': {
                'fill-color': [
                    'step',
                    ['get', 'a'],
                    '#aa0000',
                    -7.851838934271116, '#770000',
                    -0.14888551711502096, '#330000',
                    7.554067900041074, '#000000'
                ],
                'fill-outline-color': '#ffffff'
            }
        })
        self.assertEqual(self.layer.legends, [{
            'color': '#aa0000',
            'label': '[-15.554792351427212 – -7.851838934271116)',
            'shape': 'square'
        }, {
            'color': '#770000',
            'label': '[-7.851838934271116 – -0.14888551711502096)',
            'shape': 'square'
        }, {
            'color': '#330000',
            'label': '[-0.14888551711502096 – 7.554067900041074)',
            'shape': 'square'
        }, {
            'color': '#000000',
            'label': '[7.554067900041074 – 15.25702131719717]',
            'shape': 'square'
        }])

    def test_quantile_gauss(self):
        geo_layer = self.source.get_layer()

        random.seed(33)
        for index in range(0, 1000):
            self._feature_factory(geo_layer, a=random.gauss(0, 5)),

        self.layer.layer_style_wizard = {
            "property": "a",
            "symbology": "graduated",
            "method": "quantile",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, {
            'type': 'fill',
            'paint': {
                'fill-color': [
                    'step',
                    ['get', 'a'],
                    '#aa0000',
                    -3.3519812305068184, '#770000',
                    -0.011475353898097245, '#330000',
                    3.186540376312785, '#000000'
                ],
                'fill-outline-color': '#ffffff'
            }
        })
        self.assertEqual(self.layer.legends, [{
            'color': '#aa0000',
            'label': '[-15.554792351427212 – -3.3519812305068184)',
            'shape': 'square'
        }, {
            'color': '#770000',
            'label': '[-3.3519812305068184 – -0.011475353898097245)',
            'shape': 'square'
        }, {
            'color': '#330000',
            'label': '[-0.011475353898097245 – 3.186540376312785)',
            'shape': 'square'
        }, {
            'color': '#000000',
            'label': '[3.186540376312785 – 15.25702131719717]',
            'shape': 'square'
        }])

    def test_jenks_gauss(self):
        geo_layer = self.source.get_layer()

        random.seed(33)
        for index in range(0, 1000):
            self._feature_factory(geo_layer, a=random.gauss(0, 5)),

        self.layer.layer_style_wizard = {
            "property": "a",
            "symbology": "graduated",
            "method": "jenks",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, {
            'type': 'fill',
            'paint': {
                'fill-color': [
                    'step',
                    ['get', 'a'],
                    '#aa0000',
                    -4.292341999003442, '#770000',
                    0.5740581144424383, '#330000',
                    5.727211814984125, '#000000'
                ],
                'fill-outline-color': '#ffffff'
            }
        })
        self.assertEqual(self.layer.legends, [{
            'color': '#aa0000',
            'label': '[-15.554792351427212 – -4.292341999003442)',
            'shape': 'square'
        }, {
            'color': '#770000',
            'label': '[-4.292341999003442 – 0.5740581144424383)',
            'shape': 'square'
        }, {
            'color': '#330000',
            'label': '[0.5740581144424383 – 5.727211814984125)',
            'shape': 'square'
        }, {
            'color': '#000000',
            'label': '[5.727211814984125 – 15.25702131719717]',
            'shape': 'square'
        }])