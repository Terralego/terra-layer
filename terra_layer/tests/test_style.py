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
            source=self.source,
            name="my_layer_name",
            uuid="91c60192-9060-4bf6-b0de-818c5a362d89",
        )

    def _feature_factory(self, geo_layer, **properties):
        return Feature.objects.create(
            layer=geo_layer, geom=Point(-1.560408, 47.218658), properties=properties,
        )

    def test_get_min_max(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=2),

        self.assertEqual(style.get_min_max(geo_layer, "a"), [1.0, 2.0])

    def test_get_positive_min_max(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=2),

        self.assertEqual(style.get_min_max(geo_layer, "a"), [1.0, 2.0])

    def test_get_no_positive_min_max(self):
        geo_layer = self.source.get_layer()
        self.assertEqual(style.get_min_max(geo_layer, "a"), [None, None])

    def test_get_no_min_max(self):
        geo_layer = self.source.get_layer()
        self.assertEqual(style.get_min_max(geo_layer, "a"), [None, None])

    def test_circle_boundaries_0(self):
        min = 0
        max = 1
        with self.assertRaises(ValueError):
            style.circle_boundaries_candidate(min, max)

    def test_circle_boundaries_1(self):
        min = 1
        max = 1
        size = 100
        candidates = style.circle_boundaries_candidate(min, max)
        candidates = [max] + candidates + [min]
        boundaries = style.circle_boundaries_filter_values(
            candidates, min, max, size / 20
        )
        self.assertEqual(boundaries, [1])

    def test_circle_boundaries_100(self):
        min = 1
        max = 100
        size = 100
        candidates = style.circle_boundaries_candidate(min, max)
        candidates = [max] + candidates + [min]
        boundaries = style.circle_boundaries_filter_values(
            candidates, min, max, size / 20
        )
        self.assertEqual(boundaries, [100, 50, 25, 10, 5, 2.5])

    def test_circle_boundaries_001(self):
        min = 0.001
        max = 0.1
        size = 100
        candidates = style.circle_boundaries_candidate(min, max)
        candidates = [max] + candidates + [min]
        boundaries = style.circle_boundaries_filter_values(
            candidates, min, max, size / 20
        )
        # Stange
        self.assertEqual(boundaries, [0.1])
        # Should be
        # self.assertEqual(boundaries, [.1, .05, .025, .001, .0005, .00025])

    def test_circle_boundaries_none(self):
        min = None
        max = None
        size = 100
        candidates = style.circle_boundaries_candidate(min, max)
        candidates = [max] + candidates + [min]
        boundaries = style.circle_boundaries_filter_values(
            candidates, min, max, size / 20
        )
        self.assertEqual(boundaries, [])

    def test_symbology_fail(self):
        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "__666__",
        }

        with self.assertRaises(ValueError):
            self.layer.save()

    def test_method_fail(self):
        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "__666__",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }

        with self.assertRaises(ValueError):
            self.layer.save()

    def test_empty(self):
        geo_layer = self.source.get_layer()
        geo_layer.layer_style_wizard = {}
        geo_layer.save()

        # Make a random change on the layer before save
        self.layer.name = "foobar"
        self.layer.save()
        self.assertEqual(self.layer.layer_style, {})
        self.assertEqual(self.layer.legends, [])

    def test_no_wizard(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),

        self.layer.layer_style_wizard = {}
        self.layer.save()

        self.assertEqual(self.layer.layer_style, {})
        self.assertEqual(self.layer.legends, [])

    def test_0graduated_equal_interval(self):
        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "equal_interval",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, style.DEFAULT_STYLE_GRADUADED)
        self.assertEqual(self.layer.legends, [{"title": "my_layer_name"}])

    def test_0graduated_quantile(self):
        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "quantile",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, style.DEFAULT_STYLE_GRADUADED)
        self.assertEqual(self.layer.legends, [{"title": "my_layer_name"}])

    def test_0graduated_jenks(self):
        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "jenks",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, style.DEFAULT_STYLE_GRADUADED)
        self.assertEqual(self.layer.legends, [{"title": "my_layer_name"}])

    def test_update_wizard(self):
        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "jenks",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, style.DEFAULT_STYLE_GRADUADED)
        self.assertEqual(self.layer.legends, [{"title": "my_layer_name"}])

        self.layer.layer_style_wizard = {
            "field": "b",
            "symbology": "graduated",
            "method": "jenks",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, style.DEFAULT_STYLE_GRADUADED)
        self.assertEqual(self.layer.legends, [{"title": "my_layer_name"}])

    def test_2equal_interval(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=2),

        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "equal_interval",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(
            self.layer.layer_style,
            {
                "type": "fill",
                "paint": {
                    "fill-color": [
                        "step",
                        ["get", "a"],
                        "#aa0000",
                        1.25,
                        "#770000",
                        1.5,
                        "#330000",
                        1.75,
                        "#000000",
                    ],
                    "fill-opacity": 0.4,
                    "fill-outline-color": "#ffffff",
                },
            },
        )
        self.assertEqual(
            self.layer.legends,
            [
                {
                    "items": [
                        {
                            "color": "#000000",
                            "label": "[1.75 – 2.0]",
                            "shape": "square",
                        },
                        {
                            "color": "#330000",
                            "label": "[1.5 – 1.75)",
                            "shape": "square",
                        },
                        {
                            "color": "#770000",
                            "label": "[1.25 – 1.5)",
                            "shape": "square",
                        },
                        {
                            "color": "#aa0000",
                            "label": "[1.0 – 1.25)",
                            "shape": "square",
                        },
                    ],
                    "title": "my_layer_name",
                }
            ],
        )

    def test_2jenks(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=2),

        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "jenks",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(
            self.layer.layer_style,
            {
                "type": "fill",
                "paint": {
                    "fill-color": [
                        "step",
                        ["get", "a"],
                        "#aa0000",
                        2.0,
                        "#770000",
                        2.0,
                        "#330000",
                    ],
                    "fill-opacity": 0.4,
                    "fill-outline-color": "#ffffff",
                },
            },
        )
        self.assertEqual(
            self.layer.legends,
            [
                {
                    "items": [
                        {"color": "#770000", "label": "[2.0 – 2.0]", "shape": "square"},
                        {"color": "#aa0000", "label": "[1.0 – 2.0)", "shape": "square"},
                    ],
                    "title": "my_layer_name",
                }
            ],
        )

    def test_2quantile(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=2),

        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "quantile",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(
            self.layer.layer_style,
            {
                "type": "fill",
                "paint": {
                    "fill-color": [
                        "step",
                        ["get", "a"],
                        "#aa0000",
                        2,
                        "#770000",
                        2,
                        "#330000",
                    ],
                    "fill-opacity": 0.4,
                    "fill-outline-color": "#ffffff",
                },
            },
        )
        self.assertEqual(
            self.layer.legends,
            [
                {
                    "items": [
                        {"color": "#770000", "label": "[2.0 – 2.0]", "shape": "square"},
                        {"color": "#aa0000", "label": "[1.0 – 2.0)", "shape": "square"},
                    ],
                    "title": "my_layer_name",
                }
            ],
        )

    def test_0circle(self):
        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "circle",
            "max_diameter": 200,
            "fill_color": "#0000cc",
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, style.DEFAULT_STYLE_CIRCLE)
        self.assertEqual(self.layer.legends, [{"title": "my_layer_name"}])

    def test_2circle(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=128),

        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "circle",
            "max_diameter": 200,
            "fill_color": "#0000cc",
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(
            self.layer.layer_style,
            {
                "type": "circle",
                "layout": {"circle-sort-key": ["-", ["get", "a"]]},
                "paint": {
                    "circle-radius": [
                        "interpolate",
                        ["linear"],
                        ["sqrt", ["/", ["get", "a"], ["pi"]]],
                        0,
                        0,
                        6.383076486422923,
                        100,
                    ],
                    "circle-color": "#0000cc",
                    "circle-opacity": 0.4,
                    "circle-stroke-color": "#ffffff",
                    "circle-stroke-width": 0.3,
                },
            },
        )
        self.maxDiff = None
        self.assertEqual(
            self.layer.legends,
            [
                {
                    "items": [
                        {
                            "diameter": 200.0,
                            "label": "128.0",
                            "shape": "circle",
                            "color": "#0000cc",
                        },
                        {
                            "diameter": 176.77669529663686,
                            "label": "100.0",
                            "shape": "circle",
                            "color": "#0000cc",
                        },
                        {
                            "diameter": 125.0,
                            "label": "50.0",
                            "shape": "circle",
                            "color": "#0000cc",
                        },
                        {
                            "diameter": 88.38834764831843,
                            "label": "25.0",
                            "shape": "circle",
                            "color": "#0000cc",
                        },
                        {
                            "diameter": 55.90169943749474,
                            "label": "10.0",
                            "shape": "circle",
                            "color": "#0000cc",
                        },
                        {
                            "diameter": 39.528470752104745,
                            "label": "5.0",
                            "shape": "circle",
                            "color": "#0000cc",
                        },
                        {
                            "diameter": 27.95084971874737,
                            "label": "2.5",
                            "shape": "circle",
                            "color": "#0000cc",
                        },
                    ],
                    "stackedCircles": True,
                    "title": "my_layer_name",
                }
            ],
        )

    def test_gauss_graduated_equal_interval(self):
        geo_layer = self.source.get_layer()

        random.seed(33)
        for index in range(0, 1000):
            self._feature_factory(geo_layer, a=random.gauss(0, 5)),

        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "equal_interval",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(
            self.layer.layer_style,
            {
                "type": "fill",
                "paint": {
                    "fill-color": [
                        "step",
                        ["get", "a"],
                        "#aa0000",
                        -7.851838934271116,
                        "#770000",
                        -0.14888551711502096,
                        "#330000",
                        7.554067900041074,
                        "#000000",
                    ],
                    "fill-opacity": 0.4,
                    "fill-outline-color": "#ffffff",
                },
            },
        )
        self.assertEqual(
            self.layer.legends,
            [
                {
                    "items": [
                        {
                            "color": "#000000",
                            "label": "[7.554067900041074 – 15.25702131719717]",
                            "shape": "square",
                        },
                        {
                            "color": "#330000",
                            "label": "[-0.14888551711502096 – 7.554067900041074)",
                            "shape": "square",
                        },
                        {
                            "color": "#770000",
                            "label": "[-7.851838934271116 – -0.14888551711502096)",
                            "shape": "square",
                        },
                        {
                            "color": "#aa0000",
                            "label": "[-15.554792351427212 – -7.851838934271116)",
                            "shape": "square",
                        },
                    ],
                    "title": "my_layer_name",
                }
            ],
        )

    def test_gauss_graduated_quantile(self):
        geo_layer = self.source.get_layer()

        random.seed(33)
        for index in range(0, 1000):
            self._feature_factory(geo_layer, a=random.gauss(0, 5)),

        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "quantile",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(
            self.layer.layer_style,
            {
                "type": "fill",
                "paint": {
                    "fill-color": [
                        "step",
                        ["get", "a"],
                        "#aa0000",
                        -3.3519812305068184,
                        "#770000",
                        -0.011475353898097245,
                        "#330000",
                        3.186540376312785,
                        "#000000",
                    ],
                    "fill-opacity": 0.4,
                    "fill-outline-color": "#ffffff",
                },
            },
        )
        self.assertEqual(
            self.layer.legends,
            [
                {
                    "items": [
                        {
                            "color": "#000000",
                            "label": "[3.186540376312785 – 15.25702131719717]",
                            "shape": "square",
                        },
                        {
                            "color": "#330000",
                            "label": "[-0.011475353898097245 – 3.186540376312785)",
                            "shape": "square",
                        },
                        {
                            "color": "#770000",
                            "label": "[-3.3519812305068184 – -0.011475353898097245)",
                            "shape": "square",
                        },
                        {
                            "color": "#aa0000",
                            "label": "[-15.554792351427212 – -3.3519812305068184)",
                            "shape": "square",
                        },
                    ],
                    "title": "my_layer_name",
                }
            ],
        )

    def test_gauss_graduated_jenks(self):
        geo_layer = self.source.get_layer()

        random.seed(33)
        for index in range(0, 1000):
            self._feature_factory(geo_layer, a=random.gauss(0, 5)),

        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "jenks",
            "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
            "stroke_color": "#ffffff",
        }
        self.layer.save()

        self.assertEqual(
            self.layer.layer_style,
            {
                "type": "fill",
                "paint": {
                    "fill-color": [
                        "step",
                        ["get", "a"],
                        "#aa0000",
                        -4.292341999003442,
                        "#770000",
                        0.5740581144424383,
                        "#330000",
                        5.727211814984125,
                        "#000000",
                    ],
                    "fill-opacity": 0.4,
                    "fill-outline-color": "#ffffff",
                },
            },
        )
        self.assertEqual(
            self.layer.legends,
            [
                {
                    "items": [
                        {
                            "color": "#000000",
                            "label": "[5.727211814984125 – 15.25702131719717]",
                            "shape": "square",
                        },
                        {
                            "color": "#330000",
                            "label": "[0.5740581144424383 – 5.727211814984125)",
                            "shape": "square",
                        },
                        {
                            "color": "#770000",
                            "label": "[-4.292341999003442 – 0.5740581144424383)",
                            "shape": "square",
                        },
                        {
                            "color": "#aa0000",
                            "label": "[-15.554792351427212 – -4.292341999003442)",
                            "shape": "square",
                        },
                    ],
                    "title": "my_layer_name",
                }
            ],
        )
