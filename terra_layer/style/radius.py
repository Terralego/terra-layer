import math
from terra_layer.settings import (
    DEFAULT_CIRCLE_MIN_LEGEND_HEIGHT,
)

from .utils import (
    get_style_no_value_condition,
    get_positive_min_max,
    gen_style_interpolate,
    boundaries_round,
    circle_boundaries_candidate,
    circle_boundaries_filter_values,
    style_type_2_legend_shape,
)


def gen_proportionnal_radius_legend_items(
    shape,
    min,
    max,
    max_value,
    color,
    no_value_size,
    no_value_color,
):
    """
    Generate a circle legend.
    """
    candidates = circle_boundaries_candidate(min, max)
    candidates = [max] + candidates + [min]
    boundaries = circle_boundaries_filter_values(
        candidates, max, max_value, DEFAULT_CIRCLE_MIN_LEGEND_HEIGHT
    )

    r = max_value / math.sqrt(max / math.pi)

    ret = [
        {
            "diameter": math.sqrt(b / math.pi) * r,
            "size": math.sqrt(b / math.pi) * r,
            "boundaries": {"lower": {"value": b}},
            "shape": shape,
            "color": color,
        }
        for b in boundaries
    ]

    if no_value_size:
        ret.append(
            {
                "diameter": no_value_size * 2,
                "size": no_value_size * 2,
                "boundaries": {"lower": {"value": None}},
                "shape": shape,
                "color": no_value_color,
            }
        )

    return ret


def gen_proportionnal_radius_style(geo_layer, data_field, map_field, prop_config):
    field_getter = ["get", data_field]
    max_value = prop_config["max_radius"]
    no_value = prop_config.get("no_value")

    # Get min max value
    mm = get_positive_min_max(geo_layer, data_field)

    if mm[1] is not None and mm[2] is not None:
        mm = boundaries_round(mm[1:])
        boundaries = [0, math.sqrt(mm[1] / math.pi)]
        sizes = [0, max_value / 2]

        radius_base = ["sqrt", ["/", field_getter, ["pi"]]]
        radius = gen_style_interpolate(radius_base, boundaries, sizes)

        return get_style_no_value_condition(
            field_getter,
            radius,
            no_value,
        )
    else:
        return no_value or 0


def gen_proportionnal_radius_legend(
    geo_layer, data_field, map_style_type, prop_config, color, no_value_color
):
    no_value_size = prop_config.get("no_value")
    max_value = prop_config["max_radius"]

    # Get min max value
    mm = get_positive_min_max(geo_layer, data_field)

    if mm[1] is not None and mm[2] is not None:
        mm = boundaries_round(mm[1:])

        return {
            "items": gen_proportionnal_radius_legend_items(
                style_type_2_legend_shape[map_style_type],
                mm[0],
                mm[1],
                max_value,
                color,
                no_value_size,
                no_value_color,
            ),
            "stackedCircles": True,
        }
    else:
        return {
            "items": [
                {
                    "diameter": no_value_size,
                    "size": no_value_size,
                    "color": no_value_color or color,
                    "boundaries": {
                        "lower": {"value": None, "included": True},
                        "upper": {"value": None, "included": True},
                    },
                    "shape": style_type_2_legend_shape.get(map_style_type, "circle"),
                }
            ]
        }
