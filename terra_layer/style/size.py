from terra_layer.settings import (
    DEFAULT_SIZE_MIN_LEGEND_HEIGHT,
)

from .utils import (
    discretize,
    gen_style_steps,
    get_style_no_value_condition,
    get_positive_min_max,
    gen_style_interpolate,
    boundaries_round,
    size_boundaries_candidate,
    style_type_2_legend_shape,
)


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
