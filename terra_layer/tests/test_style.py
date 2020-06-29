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

        self.assertEqual(style.get_min_max(geo_layer, "a"), [False, 1.0, 2.0])

    def test_get_positive_min_max(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=2),

        self.assertEqual(style.get_min_max(geo_layer, "a"), [False, 1.0, 2.0])

    def test_get_no_positive_min_max(self):
        geo_layer = self.source.get_layer()
        self.assertEqual(style.get_min_max(geo_layer, "a"), [False, None, None])

    def test_get_no_min_max(self):
        geo_layer = self.source.get_layer()
        self.assertEqual(style.get_min_max(geo_layer, "a"), [False, None, None])

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

    def test_round_scale(self):
        self.assertEqual(style.trunc_scale(0, 3), 0)

        self.assertEqual(style.trunc_scale(111, 3), 111)
        self.assertEqual(style.trunc_scale(111, 2), 110)
        self.assertEqual(style.trunc_scale(111, 1), 100)

        self.assertEqual(style.round_scale(111, 3), 111)
        self.assertEqual(style.round_scale(111, 2), 110)
        self.assertEqual(style.round_scale(111, 1), 100)

        self.assertEqual(style.round_scale(117, 3), 117)
        self.assertEqual(style.round_scale(117, 2), 120)
        self.assertEqual(style.round_scale(117, 1), 100)

        self.assertEqual(style.ceil_scale(117, 3), 117)
        self.assertEqual(style.ceil_scale(117, 2), 120)
        self.assertEqual(style.ceil_scale(117, 1), 200)

        self.assertEqual(style.trunc_scale(0.51, 3), 0.51)
        self.assertEqual(style.trunc_scale(0.51, 2), 0.5)
        self.assertEqual(style.trunc_scale(0.51, 1), 0)

        self.assertEqual(style.round_scale(0.51, 3), 0.51)
        self.assertEqual(style.round_scale(0.51, 2), 0.5)
        self.assertEqual(style.round_scale(0.51, 1), 1)

        self.assertEqual(style.round_scale(0.49, 3), 0.49)
        self.assertEqual(style.round_scale(0.49, 2), 0.5)
        self.assertEqual(style.round_scale(0.49, 1), 0)

        self.assertEqual(style.ceil_scale(0.58, 3), 0.58)
        self.assertEqual(
            style.ceil_scale(0.58, 2), 0.6000000000000001
        )  # Got it, exactly what I want
        self.assertEqual(style.ceil_scale(0.58, 1), 1)

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
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
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
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": False,
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, style.DEFAULT_STYLE_GRADUADED)
        self.assertEqual(
            self.layer.legends,
            [{"items": [style.DEFAULT_LEGEND_GRADUADED], "title": "my_layer_name"}],
        )

    def test_0graduated_quantile(self):
        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "quantile",
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": False,
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, style.DEFAULT_STYLE_GRADUADED)
        self.assertEqual(
            self.layer.legends,
            [{"items": [style.DEFAULT_LEGEND_GRADUADED], "title": "my_layer_name"}],
        )

    def test_0graduated_jenks(self):
        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "jenks",
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": False,
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, style.DEFAULT_STYLE_GRADUADED)
        self.assertEqual(
            self.layer.legends,
            [{"items": [style.DEFAULT_LEGEND_GRADUADED], "title": "my_layer_name"}],
        )

    def test_update_wizard(self):
        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "jenks",
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": False,
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, style.DEFAULT_STYLE_GRADUADED)
        self.assertEqual(
            self.layer.legends,
            [{"items": [style.DEFAULT_LEGEND_GRADUADED], "title": "my_layer_name"}],
        )

        self.layer.layer_style_wizard = {
            "field": "b",
            "symbology": "graduated",
            "method": "jenks",
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": False,
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, style.DEFAULT_STYLE_GRADUADED)
        self.assertEqual(
            self.layer.legends,
            [{"items": [style.DEFAULT_LEGEND_GRADUADED], "title": "my_layer_name"}],
        )

    def test_boundaries_less(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=2),

        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": False,
        }
        with self.assertRaises(ValueError):
            self.layer.save()

    def test_boundaries_1(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=2),

        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "boundaries": [0],
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": False,
        }
        with self.assertRaises(ValueError):
            self.layer.save()

    def test_boundaries_no_value(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=2),

        self.layer.layer_style_wizard = {
            "field": "b",
            "symbology": "graduated",
            "method": "quantile",
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": True,
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, style.DEFAULT_STYLE_GRADUADED_NO_VALUE)
        self.assertEqual(
            self.layer.legends,
            [{"title": "my_layer_name", "items": [style.DEFAULT_LEGEND_GRADUADED]}],
        )

    def test_boundaries(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=2),

        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "boundaries": [0, 10, 20, 30, 40],
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": False,
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
                        10,
                        "#770000",
                        20,
                        "#330000",
                        30,
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
                            "boundaries": {
                                "lower": {"value": 30, "included": True},
                                "upper": {"value": 40, "included": True},
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#330000",
                            "boundaries": {
                                "lower": {"value": 20, "included": True},
                                "upper": {"value": 30, "included": False},
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#770000",
                            "boundaries": {
                                "lower": {"value": 10, "included": True},
                                "upper": {"value": 20, "included": False},
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#aa0000",
                            "boundaries": {
                                "lower": {"value": 0, "included": True},
                                "upper": {"value": 10, "included": False},
                            },
                            "shape": "square",
                        },
                    ],
                    "title": "my_layer_name",
                }
            ],
        )

    def test_boundaries_null_value(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=2),
        self._feature_factory(geo_layer, a=None),

        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "boundaries": [0, 10, 20, 30, 40],
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#fffffa",
            },
            "include_no_value": True,
        }
        self.layer.save()

        self.assertEqual(
            self.layer.layer_style,
            {
                "type": "fill",
                "paint": {
                    "fill-color": [
                        "case",
                        ["==", ["typeof", ["get", "a"]], "number"],
                        [
                            "step",
                            ["get", "a"],
                            "#aa0000",
                            10,
                            "#770000",
                            20,
                            "#330000",
                            30,
                            "#000000",
                        ],
                        "#000000",
                    ],
                    "fill-opacity": [
                        "case",
                        ["==", ["typeof", ["get", "a"]], "number"],
                        0.4,
                        0,
                    ],
                    "fill-outline-color": [
                        "case",
                        ["==", ["typeof", ["get", "a"]], "number"],
                        "#fffffa",
                        "#ffffff",
                    ],
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
                            "boundaries": {
                                "lower": {"value": 30, "included": True},
                                "upper": {"value": 40, "included": True},
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#330000",
                            "boundaries": {
                                "lower": {"value": 20, "included": True},
                                "upper": {"value": 30, "included": False},
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#770000",
                            "boundaries": {
                                "lower": {"value": 10, "included": True},
                                "upper": {"value": 20, "included": False},
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#aa0000",
                            "boundaries": {
                                "lower": {"value": 0, "included": True},
                                "upper": {"value": 10, "included": False},
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#000000",
                            "boundaries": {
                                "lower": {"value": None, "included": True},
                                "upper": {"value": None, "included": True},
                            },
                            "shape": "square",
                        },
                    ],
                    "title": "my_layer_name",
                }
            ],
        )

    def test_2equal_interval(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=2),

        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "equal_interval",
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": False,
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
                            "boundaries": {
                                "lower": {"value": 1.75, "included": True},
                                "upper": {"value": 2.0, "included": True},
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#330000",
                            "boundaries": {
                                "lower": {"value": 1.5, "included": True},
                                "upper": {"value": 1.75, "included": False},
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#770000",
                            "boundaries": {
                                "lower": {"value": 1.25, "included": True},
                                "upper": {"value": 1.5, "included": False},
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#aa0000",
                            "boundaries": {
                                "lower": {"value": 1.0, "included": True},
                                "upper": {"value": 1.25, "included": False},
                            },
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
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": False,
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
                        {
                            "color": "#770000",
                            "boundaries": {
                                "lower": {"value": 2.0, "included": True},
                                "upper": {"value": 2.0, "included": True},
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#aa0000",
                            "boundaries": {
                                "lower": {"value": 1.0, "included": True},
                                "upper": {"value": 2.0, "included": False},
                            },
                            "shape": "square",
                        },
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
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": False,
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
                        {
                            "color": "#770000",
                            "boundaries": {
                                "lower": {"value": 2.0, "included": True},
                                "upper": {"value": 2.0, "included": True},
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#aa0000",
                            "boundaries": {
                                "lower": {"value": 1.0, "included": True},
                                "upper": {"value": 2.0, "included": False},
                            },
                            "shape": "square",
                        },
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
            "style": {"fill_color": "#0000cc", "stroke_color": "#ffffff"},
            "include_no_value": False,
        }
        self.layer.save()

        self.assertEqual(self.layer.layer_style, style.DEFAULT_STYLE_CIRCLE)
        self.assertEqual(self.layer.legends, [{"title": "my_layer_name"}])

    def test_2circle(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=0),
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=129),

        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "circle",
            "max_diameter": 200,
            "style": {"fill_color": "#0000cc", "stroke_color": "#ffffff"},
            "include_no_value": False,
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
                        6.432750982580687,
                        100,
                    ],
                    "circle-color": "#0000cc",
                    "circle-opacity": 0.4,
                    "circle-stroke-color": "#ffffff",
                    "circle-stroke-width": 0.3,
                },
            },
        )
        self.assertEqual(
            self.layer.legends,
            [
                {
                    "items": [
                        {
                            "diameter": 200.0,
                            "boundaries": {"lower": {"value": 130}},
                            "shape": "circle",
                            "color": "#0000cc",
                        },
                        {
                            "diameter": 175.41160386140584,
                            "boundaries": {"lower": {"value": 100.0}},
                            "shape": "circle",
                            "color": "#0000cc",
                        },
                        {
                            "diameter": 124.03473458920845,
                            "boundaries": {"lower": {"value": 50.0}},
                            "shape": "circle",
                            "color": "#0000cc",
                        },
                        {
                            "diameter": 87.70580193070292,
                            "boundaries": {"lower": {"value": 25.0}},
                            "shape": "circle",
                            "color": "#0000cc",
                        },
                        {
                            "diameter": 55.47001962252292,
                            "boundaries": {"lower": {"value": 10.0}},
                            "shape": "circle",
                            "color": "#0000cc",
                        },
                        {
                            "diameter": 39.22322702763681,
                            "boundaries": {"lower": {"value": 5.0}},
                            "shape": "circle",
                            "color": "#0000cc",
                        },
                    ],
                    "stackedCircles": True,
                    "title": "my_layer_name",
                }
            ],
        )

    def test_2circle_no_value(self):
        geo_layer = self.source.get_layer()
        self._feature_factory(geo_layer, a=0),
        self._feature_factory(geo_layer, a=1),
        self._feature_factory(geo_layer, a=129),

        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "circle",
            "max_diameter": 200,
            "style": {"fill_color": "#0000ca", "stroke_color": "#fffffa"},
            "include_no_value": True,
        }
        self.layer.save()

        interpolate = [
            "interpolate",
            ["linear"],
            ["sqrt", ["/", ["get", "a"], ["pi"]]],
            0,
            0,
            6.432750982580687,
            100.0,
        ]
        self.assertEqual(
            self.layer.layer_style,
            {
                "type": "circle",
                "layout": {"circle-sort-key": ["-", ["get", "a"]]},
                "paint": {
                    "circle-radius": [
                        "case",
                        ["==", ["typeof", interpolate], "number"],
                        interpolate,
                        30,
                    ],
                    "circle-color": [
                        "case",
                        ["==", ["typeof", interpolate], "number"],
                        "#0000ca",
                        "#000000",
                    ],
                    "circle-opacity": [
                        "case",
                        ["==", ["typeof", interpolate], "number"],
                        0.4,
                        0,
                    ],
                    "circle-stroke-color": [
                        "case",
                        ["==", ["typeof", interpolate], "number"],
                        "#fffffa",
                        "#ffffff",
                    ],
                    "circle-stroke-width": [
                        "case",
                        ["==", ["typeof", interpolate], "number"],
                        0.3,
                        0.3,
                    ],
                },
            },
        )
        self.assertEqual(
            self.layer.legends,
            [
                {
                    "items": [
                        {
                            "diameter": 200.0,
                            "boundaries": {"lower": {"value": 130}},
                            "shape": "circle",
                            "color": "#0000ca",
                        },
                        {
                            "diameter": 175.41160386140584,
                            "boundaries": {"lower": {"value": 100.0}},
                            "shape": "circle",
                            "color": "#0000ca",
                        },
                        {
                            "diameter": 124.03473458920845,
                            "boundaries": {"lower": {"value": 50.0}},
                            "shape": "circle",
                            "color": "#0000ca",
                        },
                        {
                            "diameter": 87.70580193070292,
                            "boundaries": {"lower": {"value": 25.0}},
                            "shape": "circle",
                            "color": "#0000ca",
                        },
                        {
                            "diameter": 55.47001962252292,
                            "boundaries": {"lower": {"value": 10.0}},
                            "shape": "circle",
                            "color": "#0000ca",
                        },
                        {
                            "diameter": 39.22322702763681,
                            "boundaries": {"lower": {"value": 5.0}},
                            "shape": "circle",
                            "color": "#0000ca",
                        },
                        {
                            "diameter": 60,
                            "boundaries": {"lower": {"value": None}},
                            "shape": "circle",
                            "color": "#000000",
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
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": False,
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
                            "boundaries": {
                                "lower": {"value": 7.554067900041074, "included": True},
                                "upper": {"value": 15.25702131719717, "included": True},
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#330000",
                            "boundaries": {
                                "lower": {
                                    "value": -0.14888551711502096,
                                    "included": True,
                                },
                                "upper": {
                                    "value": 7.554067900041074,
                                    "included": False,
                                },
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#770000",
                            "boundaries": {
                                "lower": {
                                    "value": -7.851838934271116,
                                    "included": True,
                                },
                                "upper": {
                                    "value": -0.14888551711502096,
                                    "included": False,
                                },
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#aa0000",
                            "boundaries": {
                                "lower": {
                                    "value": -15.554792351427212,
                                    "included": True,
                                },
                                "upper": {
                                    "value": -7.851838934271116,
                                    "included": False,
                                },
                            },
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
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": False,
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
                            "boundaries": {
                                "lower": {"value": 3.186540376312785, "included": True},
                                "upper": {
                                    "value": 15.25702131719717,
                                    "included": True,
                                },
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#330000",
                            "boundaries": {
                                "lower": {
                                    "value": -0.011475353898097245,
                                    "included": True,
                                },
                                "upper": {
                                    "value": 3.186540376312785,
                                    "included": False,
                                },
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#770000",
                            "boundaries": {
                                "lower": {
                                    "value": -3.3519812305068184,
                                    "included": True,
                                },
                                "upper": {
                                    "value": -0.011475353898097245,
                                    "included": False,
                                },
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#aa0000",
                            "boundaries": {
                                "lower": {
                                    "value": -15.554792351427212,
                                    "included": True,
                                },
                                "upper": {
                                    "value": -3.3519812305068184,
                                    "included": False,
                                },
                            },
                            "shape": "square",
                        },
                    ],
                    "title": "my_layer_name",
                }
            ],
        )

    def test_gauss_graduated_quantile_white_none(self):
        geo_layer = self.source.get_layer()

        random.seed(33)
        for index in range(0, 1000):
            self._feature_factory(geo_layer, a=random.gauss(0, 5)),
        for index in range(0, 10):
            self._feature_factory(geo_layer, a=None),

        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "quantile",
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": True,
        }
        self.layer.save()
        self.maxDiff = None

        self.assertEqual(
            self.layer.layer_style,
            {
                "type": "fill",
                "paint": {
                    "fill-color": [
                        "case",
                        ["==", ["typeof", ["get", "a"]], "number"],
                        [
                            "step",
                            ["get", "a"],
                            "#aa0000",
                            -3.307794810850208,
                            "#770000",
                            0.020384992547665716,
                            "#330000",
                            3.256429352130346,
                            "#000000",
                        ],
                        "#000000",
                    ],
                    "fill-opacity": [
                        "case",
                        ["==", ["typeof", ["get", "a"]], "number"],
                        0.4,
                        0,
                    ],
                    "fill-outline-color": [
                        "case",
                        ["==", ["typeof", ["get", "a"]], "number"],
                        "#ffffff",
                        "#ffffff",
                    ],
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
                            "boundaries": {
                                "lower": {"value": 3.256429352130346, "included": True},
                                "upper": {
                                    "value": 15.25702131719717,
                                    "included": True,
                                },
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#330000",
                            "boundaries": {
                                "lower": {
                                    "value": 0.020384992547665716,
                                    "included": True,
                                },
                                "upper": {
                                    "value": 3.256429352130346,
                                    "included": False,
                                },
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#770000",
                            "boundaries": {
                                "lower": {
                                    "value": -3.307794810850208,
                                    "included": True,
                                },
                                "upper": {
                                    "value": 0.020384992547665716,
                                    "included": False,
                                },
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#aa0000",
                            "boundaries": {
                                "lower": {
                                    "value": -15.554792351427212,
                                    "included": True,
                                },
                                "upper": {
                                    "value": -3.307794810850208,
                                    "included": False,
                                },
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#000000",
                            "boundaries": {
                                "lower": {"value": None, "included": True},
                                "upper": {"value": None, "included": True},
                            },
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
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": False,
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
                            "boundaries": {
                                "lower": {"value": 5.727211814984125, "included": True},
                                "upper": {
                                    "value": 15.25702131719717,
                                    "included": True,
                                },
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#330000",
                            "boundaries": {
                                "lower": {
                                    "value": 0.5740581144424383,
                                    "included": True,
                                },
                                "upper": {
                                    "value": 5.727211814984125,
                                    "included": False,
                                },
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#770000",
                            "boundaries": {
                                "lower": {
                                    "value": -4.292341999003442,
                                    "included": True,
                                },
                                "upper": {
                                    "value": 0.5740581144424383,
                                    "included": False,
                                },
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#aa0000",
                            "boundaries": {
                                "lower": {
                                    "value": -15.554792351427212,
                                    "included": True,
                                },
                                "upper": {
                                    "value": -4.292341999003442,
                                    "included": False,
                                },
                            },
                            "shape": "square",
                        },
                    ],
                    "title": "my_layer_name",
                }
            ],
        )

    def test_graduated_jenks_only_none(self):
        geo_layer = self.source.get_layer()

        self._feature_factory(geo_layer, a=None),

        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "jenks",
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": True,
            "no_value_style": {
                "fill_color": "#CC0000",
                "fill_opacity": 0.5,
                "stroke_color": "#00ffff",
            },
        }
        self.layer.save()
        self.maxDiff = None

        self.assertEqual(
            self.layer.layer_style,
            {
                "type": "fill",
                "paint": {
                    "fill-color": "#CC0000",
                    "fill-opacity": 0.5,
                    "fill-outline-color": "#00ffff",
                },
            },
        )
        self.assertEqual(
            self.layer.legends,
            [
                {
                    "items": [
                        {
                            "color": "#CC0000",
                            "boundaries": {
                                "lower": {"value": None, "included": True},
                                "upper": {"value": None, "included": True},
                            },
                            "shape": "square",
                        },
                    ],
                    "title": "my_layer_name",
                }
            ],
        )

    def test_gauss_graduated_jenks_with_none(self):
        geo_layer = self.source.get_layer()

        random.seed(33)
        for index in range(0, 1000):
            self._feature_factory(geo_layer, a=random.gauss(0, 5)),
        for index in range(0, 10):
            self._feature_factory(geo_layer, a=None),

        self.layer.layer_style_wizard = {
            "field": "a",
            "symbology": "graduated",
            "method": "jenks",
            "style": {
                "fill_color": ["#aa0000", "#770000", "#330000", "#000000"],
                "stroke_color": "#ffffff",
            },
            "include_no_value": True,
            "no_value_style": {
                "fill_color": "#CC0000",
                "fill_opacity": 0.5,
                "stroke_color": "#00ffff",
            },
        }
        self.layer.save()

        self.assertEqual(
            self.layer.layer_style,
            {
                "type": "fill",
                "paint": {
                    "fill-color": [
                        "case",
                        ["==", ["typeof", ["get", "a"]], "number"],
                        [
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
                        "#CC0000",
                    ],
                    "fill-opacity": [
                        "case",
                        ["==", ["typeof", ["get", "a"]], "number"],
                        0.4,
                        0.5,
                    ],
                    "fill-outline-color": [
                        "case",
                        ["==", ["typeof", ["get", "a"]], "number"],
                        "#ffffff",
                        "#00ffff",
                    ],
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
                            "boundaries": {
                                "lower": {"value": 5.727211814984125, "included": True},
                                "upper": {
                                    "value": 15.25702131719717,
                                    "included": True,
                                },
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#330000",
                            "boundaries": {
                                "lower": {
                                    "value": 0.5740581144424383,
                                    "included": True,
                                },
                                "upper": {
                                    "value": 5.727211814984125,
                                    "included": False,
                                },
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#770000",
                            "boundaries": {
                                "lower": {
                                    "value": -4.292341999003442,
                                    "included": True,
                                },
                                "upper": {
                                    "value": 0.5740581144424383,
                                    "included": False,
                                },
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#aa0000",
                            "boundaries": {
                                "lower": {
                                    "value": -15.554792351427212,
                                    "included": True,
                                },
                                "upper": {
                                    "value": -4.292341999003442,
                                    "included": False,
                                },
                            },
                            "shape": "square",
                        },
                        {
                            "color": "#CC0000",
                            "boundaries": {
                                "lower": {"value": None, "included": True},
                                "upper": {"value": None, "included": True},
                            },
                            "shape": "square",
                        },
                    ],
                    "title": "my_layer_name",
                }
            ],
        )
