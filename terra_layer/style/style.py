from django.db import connection
import numbers
import math
from functools import reduce
from terra_layer.settings import (
    DEFAULT_CIRCLE_MIN_LEGEND_HEIGHT,
    DEFAULT_SIZE_MIN_LEGEND_HEIGHT,
    DEFAULT_NO_VALUE_FILL_COLOR,
)

from .utils import (
    discretize,
    gen_style_steps,
    get_style_no_value_condition,
    get_positive_min_max,
    gen_style_interpolate,
    boundaries_round,
    size_boundaries_candidate,
    circle_boundaries_candidate,
    circle_boundaries_filter_values,
)


def to_map_style(prop):
    return prop.replace("_", "-")


style_type_2_legend_shape = {
    "fill-extrusion": "square",
    "fill": "square",
    "circle": "circle",
    "symbol": "symbol",
    "line": "line",
}


def field_2_variation_type(field):
    if "color" in field:
        return "color"
    if "width" in field or "height" in field:
        return "value"
    if "radius" in field or "size" in field:
        return "radius"


def gen_color_legend_steps(boundaries, colors, no_value_color, shape="square"):
    """
    Generate a discrete color legend.
    """
    size = len(boundaries) - 1
    ret = [
        {
            "color": colors[index],
            "boundaries": {
                "lower": {"value": boundaries[index], "included": True},
                "upper": {
                    "value": boundaries[index + 1],
                    "included": index + 1 == size,
                },
            },
            "shape": shape,
        }
        for index in range(size)
    ]

    if no_value_color:
        ret.insert(
            0,
            {
                "color": no_value_color,
                "boundaries": {
                    "lower": {"value": None, "included": True},
                    "upper": {"value": None, "included": True},
                },
                "shape": shape,
            },
        )

    return ret


def gen_size_legend_steps(
    boundaries, values, color, no_value, no_value_color, shape="square"
):
    """
    Generate a discrete size legend.
    """
    size = len(boundaries) - 1
    ret = [
        {
            "color": color,
            "size": values[index],
            "boundaries": {
                "lower": {"value": boundaries[index], "included": True},
                "upper": {
                    "value": boundaries[index + 1],
                    "included": index + 1 == size,
                },
            },
            "shape": shape,
        }
        for index in range(size)
    ]

    if no_value:
        ret.insert(
            0,
            {
                "color": no_value_color or color,
                "size": no_value,
                "boundaries": {
                    "lower": {"value": None, "included": True},
                    "upper": {"value": None, "included": True},
                },
                "shape": shape,
            },
        )

    return ret


def gen_proportionnal_size_legend_items(
    shape,  # line, square, circle
    min,
    max,
    max_value,
    color,
    no_value_size,
    no_value_color,
):
    """
    Generate a proportionnal size legend
    """
    if min <= DEFAULT_SIZE_MIN_LEGEND_HEIGHT:
        min = DEFAULT_SIZE_MIN_LEGEND_HEIGHT

    candidates = size_boundaries_candidate(min, max)
    boundaries = [max] + candidates + [min]

    ret = [
        {
            "size": (b / max) * max_value,
            "boundaries": {"lower": {"value": b}},
            "shape": shape,
            "color": color,
        }
        for b in boundaries
    ]

    if no_value_size:
        ret.append(
            {
                "size": no_value_size,
                "boundaries": {"lower": {"value": None}},
                "shape": shape,
                "color": no_value_color,
            }
        )

    return ret


def gen_proportionnal_circle_legend_items(
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


def gen_graduated_color_style(geo_layer, data_field, map_field, prop_config):
    colors = prop_config["values"]
    no_value = prop_config.get("no_value")

    # Step 1 generate boundaries
    if "boundaries" in prop_config:
        boundaries = prop_config["boundaries"]
        if len(boundaries) < 2:
            raise ValueError('"boundaries" must be at least a list of two values')
    elif "method" in prop_config:
        boundaries = discretize(
            geo_layer, data_field, prop_config["method"], len(colors)
        )
    else:
        raise ValueError(
            'With "graduated" analysis, "boundaries" or "method" should be provided'
        )

    # Use boundaries to make style
    if boundaries is not None:
        field_getter = ["get", data_field]

        style_steps = gen_style_steps(field_getter, boundaries, colors)

        return get_style_no_value_condition(
            field_getter,
            style_steps,
            no_value,
        )
    else:
        return no_value or colors[0]


def gen_graduated_color_legend(geo_layer, data_field, map_style_type, prop_config):
    colors = prop_config["values"]
    no_value = prop_config.get("no_value")

    # Step 1 generate boundaries
    if "boundaries" in prop_config:
        boundaries = prop_config["boundaries"]
    elif "method" in prop_config:
        boundaries = discretize(
            geo_layer, data_field, prop_config["method"], len(colors)
        )

    # Use boundaries to make style
    if boundaries is not None:
        return {
            "items": gen_color_legend_steps(
                boundaries,
                colors,
                no_value,
            )[::-1],
        }
    else:
        color = colors[0]
        if no_value:
            color = no_value

        return {
            "items": [
                {
                    "color": color,
                    "boundaries": {
                        "lower": {"value": None, "included": True},
                        "upper": {"value": None, "included": True},
                    },
                    "shape": style_type_2_legend_shape.get(map_style_type, "square"),
                }
            ]
        }


def gen_categorized_value_style(geo_layer, data_field, prop_config, default_no_value):
    default_value = None
    field_getter = ["get", data_field]

    if not prop_config["categories"]:
        return None

    steps = ["match", field_getter]
    for category in prop_config["categories"]:
        name = category["name"]
        value = category["value"]
        if name is None:
            default_value = value
            continue

        steps.append(name)
        steps.append(value)

    steps.append(default_value or default_no_value)

    if default_value is not None:
        return ["case", ["has", data_field], steps, default_value]
    else:
        return steps


def gen_categorized_value_legend(
    map_style_type,
    prop_config,
    legend_field="size",
    other_properties=None,
):
    other_properties = other_properties or {}

    default_value = None
    shape = style_type_2_legend_shape.get(map_style_type, "square")

    items = []
    for category in prop_config["categories"]:
        name = category["name"]
        value = category["value"]
        if name is None:
            default_value = value
            continue

        items.append(
            {legend_field: value, "label": name, "shape": shape, **other_properties}
        )

    if default_value is not None:
        items.append(
            {legend_field: value, "label": None, "shape": shape, **other_properties}
        )

    return {"items": items}


def gen_graduated_size_style(geo_layer, data_field, map_field, prop_config):
    values = prop_config["values"]
    no_value = prop_config.get("no_value")

    # Step 1 generate boundaries
    if "boundaries" in prop_config:
        boundaries = prop_config["boundaries"]
        if len(boundaries) < 2:
            raise ValueError('"boundaries" must be at least a list of two values')
    elif "method" in prop_config:
        boundaries = discretize(
            geo_layer, data_field, prop_config["method"], len(values)
        )
    else:
        raise ValueError(
            'With "graduated" analysis, "boundaries" or "method" should be provided'
        )

    # Use boundaries to make style
    if boundaries is not None:
        field_getter = ["get", data_field]

        style_steps = gen_style_steps(field_getter, boundaries, values)

        return get_style_no_value_condition(
            field_getter,
            style_steps,
            no_value,
        )
    else:
        return no_value or values[0]


def gen_graduated_size_legend(
    geo_layer, data_field, map_style_type, prop_config, color, no_value_color
):
    values = prop_config["values"]
    no_value = prop_config.get("no_value")

    # Step 1 generate boundaries
    if "boundaries" in prop_config:
        boundaries = prop_config["boundaries"]
    elif "method" in prop_config:
        boundaries = discretize(
            geo_layer, data_field, prop_config["method"], len(values)
        )

    # Use boundaries to make style
    if boundaries is not None:
        return {
            "items": gen_size_legend_steps(
                boundaries,
                values,
                color,
                no_value,
                no_value_color,
                style_type_2_legend_shape.get(map_style_type, "square"),
            )[::-1],
        }
    else:
        return {
            "items": [
                {
                    "color": no_value_color or color,
                    "boundaries": {
                        "lower": {"value": None, "included": True},
                        "upper": {"value": None, "included": True},
                    },
                    "shape": style_type_2_legend_shape.get(map_style_type, "square"),
                }
            ]
        }


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
            "items": gen_proportionnal_circle_legend_items(
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


def gen_proportionnal_size_style(geo_layer, data_field, map_field, prop_config):
    field_getter = ["get", data_field]
    max_value = prop_config["max_value"]
    no_value = prop_config.get("no_value")

    # Get min max value
    mm = get_positive_min_max(geo_layer, data_field)

    if mm[1] is not None and mm[2] is not None:
        mm = boundaries_round(mm[1:])
        boundaries = [0, mm[1]]
        sizes = [0, max_value]

        interpolation = gen_style_interpolate(field_getter, boundaries, sizes)

        return get_style_no_value_condition(
            field_getter,
            interpolation,
            no_value,
        )
    else:
        return no_value or 0


def gen_proportionnal_size_legend(
    geo_layer, data_field, map_style_type, prop_config, color, no_value_color
):
    no_value_size = prop_config.get("no_value")
    max_value = prop_config["max_value"]

    # Get min max value
    mm = get_positive_min_max(geo_layer, data_field)

    if mm[1] is not None and mm[2] is not None:
        mm = boundaries_round(mm[1:])

        return {
            "items": gen_proportionnal_size_legend_items(
                style_type_2_legend_shape[map_style_type],
                mm[0],
                mm[1],
                max_value,
                color,
                no_value_size,
                no_value_color,
            ),
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


def generate_style_from_wizard(geo_layer, config):
    """
    Return a Mapbox GL Style and a Legend from a wizard setting.
    """

    # fill, fill_extrusion, line, text, symbol, circle
    map_style_type = config["map_style_type"]

    map_style = {"type": map_style_type, "paint": {}}

    legends = []

    for map_field, prop_config in config["style"].items():
        style_type = prop_config.get("type", "none")

        # Ignore style from other representation
        if not map_field.replace("fill_extrusion", "extrusion").startswith(
            map_style_type.replace("fill-extrusion", "extrusion")
        ):
            continue

        map_style_prop = to_map_style(map_field)
        if style_type == "fixed":
            # Fixed value
            value = prop_config["value"]
            no_value = prop_config.get("no_value")
            data_field = prop_config.get("field")
            map_style["paint"][map_style_prop] = get_style_no_value_condition(
                ["get", data_field], value, no_value
            )
        elif style_type == "variable":
            # Variable style
            data_field = prop_config["field"]
            variation_type = field_2_variation_type(map_field)
            analysis = prop_config["analysis"]

            if variation_type == "color":
                if analysis == "graduated":
                    map_style["paint"][map_style_prop] = gen_graduated_color_style(
                        geo_layer, data_field, map_field, prop_config
                    )
                    if prop_config.get("generate_legend"):
                        # TODO reuse previous computations
                        legends.append(
                            gen_graduated_color_legend(
                                geo_layer, data_field, map_style_type, prop_config
                            )
                        )
                elif analysis == "categorized":
                    map_style["paint"][map_style_prop] = gen_categorized_value_style(
                        geo_layer, data_field, prop_config, DEFAULT_NO_VALUE_FILL_COLOR
                    )
                    if map_style["paint"][map_style_prop] is None:
                        del map_style["paint"][map_style_prop]

                    if prop_config.get("generate_legend"):
                        legends.append(
                            gen_categorized_value_legend(
                                map_style_type,
                                prop_config,
                                "color",
                            )
                        )
                else:
                    raise ValueError(f'Unhandled analysis type "{analysis}"')

            if variation_type == "radius":
                if analysis == "categorized":
                    map_style["paint"][map_style_prop] = gen_categorized_value_style(
                        geo_layer, data_field, prop_config, 0
                    )
                    if map_style["paint"][map_style_prop] is None:
                        del map_style["paint"][map_style_prop]

                    if prop_config.get("generate_legend"):
                        color = (
                            config["style"]
                            .get(f"{map_style_type}_color", {})
                            .get("value", DEFAULT_NO_VALUE_FILL_COLOR)
                        )
                        legends.append(
                            gen_categorized_value_legend(
                                map_style_type,
                                prop_config,
                                "size",
                                other_properties={"color": color},
                            )
                        )
                elif analysis == "proportionnal":
                    map_style["paint"][map_style_prop] = gen_proportionnal_radius_style(
                        geo_layer, data_field, map_field, prop_config
                    )
                    # Add sort key
                    # TODO find more intelligent way to do that
                    map_style["layout"] = {
                        f"{map_style_type}-sort-key": ["-", ["get", data_field]]
                    }
                    if prop_config.get("generate_legend"):
                        # TODO reuse previous computations
                        color = (
                            config["style"]
                            .get(f"{map_style_type}_color", {})
                            .get("value", DEFAULT_NO_VALUE_FILL_COLOR)
                        )
                        no_value_color = (
                            config["style"]
                            .get(f"{map_style_type}_color", {})
                            .get("no_value")
                        )
                        legends.append(
                            gen_proportionnal_radius_legend(
                                geo_layer,
                                data_field,
                                map_style_type,
                                prop_config,
                                color,
                                no_value_color,
                            )
                        )
                else:
                    raise ValueError(f'Unhandled analysis type "{analysis}"')

            if variation_type == "value":
                if analysis == "graduated":
                    map_style["paint"][map_style_prop] = gen_graduated_size_style(
                        geo_layer, data_field, map_field, prop_config
                    )
                    if prop_config.get("generate_legend"):
                        # TODO reuse previous computations
                        color = (
                            config["style"]
                            .get(f"{map_style_type}_color", {})
                            .get("value", DEFAULT_NO_VALUE_FILL_COLOR)
                        )
                        no_value_color = (
                            config["style"]
                            .get(f"{map_style_type}_color", {})
                            .get("no_value")
                        )
                        legends.append(
                            gen_graduated_size_legend(
                                geo_layer,
                                data_field,
                                map_style_type,
                                prop_config,
                                color,
                                no_value_color,
                            )
                        )
                elif analysis == "categorized":
                    map_style["paint"][map_style_prop] = gen_categorized_value_style(
                        geo_layer, data_field, prop_config, 0
                    )
                    if map_style["paint"][map_style_prop] is None:
                        del map_style["paint"][map_style_prop]

                    if prop_config.get("generate_legend"):
                        color = (
                            config["style"]
                            .get(f"{map_style_type}_color", {})
                            .get("value", DEFAULT_NO_VALUE_FILL_COLOR)
                        )
                        legends.append(
                            gen_categorized_value_legend(
                                map_style_type,
                                prop_config,
                                "size",
                                other_properties={"color": color},
                            )
                        )
                elif analysis == "proportionnal":
                    """map_style["layout"] = {
                        f"{map_style_type}-sort-key": ["-", ["get", data_field]]
                    }"""
                    map_style["paint"][map_style_prop] = gen_proportionnal_size_style(
                        geo_layer, data_field, map_field, prop_config
                    )
                    if prop_config.get("generate_legend"):
                        # TODO reuse previous computations
                        color = (
                            config["style"]
                            .get(f"{map_style_type}_color", {})
                            .get("value", DEFAULT_NO_VALUE_FILL_COLOR)
                        )
                        no_value_color = (
                            config["style"]
                            .get(f"{map_style_type}_color", {})
                            .get("no_value")
                        )
                        legends.append(
                            gen_proportionnal_size_legend(
                                geo_layer,
                                data_field,
                                map_style_type,
                                prop_config,
                                color,
                                no_value_color,
                            )
                        )
                else:
                    raise ValueError(f'Unknow analysis type "{analysis}"')

    return (map_style, legends)
