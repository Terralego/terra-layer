from django.db import connection
import numbers
import math
from functools import reduce
from terra_layer.settings import (
    DEFAULT_CIRCLE_MIN_LEGEND_HEIGHT,
    DEFAULT_NO_VALUE_FILL_COLOR,
    DEFAULT_NO_VALUE_CIRCLE_RADIUS,
)

DEFAULT_LEGEND_GRADUADED = {
    "color": DEFAULT_NO_VALUE_FILL_COLOR,
    "boundaries": {
        "lower": {"value": None, "included": True},
        "upper": {"value": None, "included": True},
    },
    "shape": "square",
}

DEFAULT_LEGEND_CIRCLE = {
    "diameter": DEFAULT_NO_VALUE_CIRCLE_RADIUS * 2,
    "boundaries": {"lower": {"value": None}},
    "shape": "circle",
    "color": DEFAULT_NO_VALUE_FILL_COLOR,
}


def _flatten(levels):
    """
    Flatten 2-level array.
    [[1,2], [3, 4, 5]] -> [1, 2, 3, 4, 5]
    """
    return list(reduce(lambda x, y: x + y, levels or []))


def get_min_max(geo_layer, field):
    """
    Return the max and the min value of a property.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                bool_or((properties->>%(field)s)::numeric IS NULL) AS is_null,
                min((properties->>%(field)s)::numeric) AS min,
                max((properties->>%(field)s)::numeric) AS max
            FROM
                geostore_feature
            WHERE
                layer_id = %(layer_id)s
            """,
            {"field": field, "layer_id": geo_layer.id},
        )
        row = cursor.fetchone()
        is_null, min, max = row
        return [is_null == True, min, max]  # noqa


def get_positive_min_max(geo_layer, field):
    """
    Return the max and the min value of a property.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                bool_or((properties->>%(field)s)::numeric IS NULL) AS is_null,
                min((properties->>%(field)s)::numeric) AS min,
                max((properties->>%(field)s)::numeric) AS max
            FROM
                geostore_feature
            WHERE
                layer_id = %(layer_id)s AND
                (properties->>%(field)s)::numeric > 0
            """,
            {"field": field, "layer_id": geo_layer.id},
        )
        row = cursor.fetchone()
        is_null, min, max = row
        return [is_null == True, min, max]  # noqa


def discretize_quantile(geo_layer, field, class_count):
    """
    Compute Quantile class boundaries from a layer property.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH
            ntiles AS (
                SELECT
                    (properties->>%(field)s)::numeric AS value,
                    ntile(%(class_count)s) OVER (ORDER BY (properties->>%(field)s)::numeric) AS ntile
                FROM
                    geostore_feature
                WHERE
                    layer_id = %(layer_id)s
                UNION ALL
                SELECT
                    NULL AS value,
                    NULL AS ntile
                FROM
                    geostore_feature
                WHERE
                    layer_id = %(layer_id)s AND
                    (properties->>%(field)s)::numeric IS NOT NULL
            )
            SELECT
                min(value) AS boundary,
                max(value) AS max
            FROM
                ntiles
            GROUP BY
                ntile
            ORDER BY
                ntile
            """,
            {"field": field, "class_count": class_count, "layer_id": geo_layer.id},
        )
        rows = cursor.fetchall()
        if rows and len(rows) > 0:
            rows = [row for row in rows if row[0] is not None]
            if len(rows) == 0:
                return []
            else:
                # Each class start + last class end
                return [r[0] for r in rows] + [rows[-1][1]]


def discretize_jenks(geo_layer, field, class_count):
    """
    Compute Jenks class boundaries from a layer property.
    Note: Use PostGIS ST_ClusterKMeans() as k-means function.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH
            kmeans AS (
                SELECT
                    (properties->>%(field)s)::numeric AS field,
                    ST_ClusterKMeans(
                        ST_MakePoint((properties->>%(field)s)::numeric, 0),
                        least(%(class_count)s, (SELECT count(*) FROM geostore_feature WHERE layer_id = %(layer_id)s))::integer
                    ) OVER () AS class_id
                FROM
                    geostore_feature
                WHERE
                    layer_id = %(layer_id)s
            )
            SELECT
                min(field) AS min,
                max(field) AS max
            FROM
                kmeans
            GROUP BY
                class_id
            ORDER BY
                min,
                max
            """,
            {"field": field, "class_count": class_count, "layer_id": geo_layer.id},
        )
        rows = cursor.fetchall()
        if rows and len(rows) > 0:
            rows = [row for row in rows if row[0] is not None]
            if len(rows) == 0:
                return []
            else:
                # Each class start + last class end
                return [r[0] for r in rows] + [rows[-1][1]]


def discretize_equal_interval(geo_layer, field, class_count):
    """
    Compute QuantiEqual Interval class boundaries from a layer property.
    """
    is_null, min, max = get_min_max(geo_layer, field)
    if min is not None and max is not None and isinstance(min, numbers.Number):
        delta = (max - min) / class_count
        return [min + delta * i for i in range(0, class_count + 1)]
    else:
        # TODO was return []
        return None


def discretize(geo_layer, field, method, class_count):
    """
    Select a method to compute class boundaries.
    Compute (len(class_count) + 1) boundaries.
    Note, can returns less boundaries than requested if lesser values in property than class_count
    """
    if method == "quantile":
        return discretize_quantile(geo_layer, field, class_count)
    elif method == "jenks":
        return discretize_jenks(geo_layer, field, class_count)
    elif method == "equal_interval":
        return discretize_equal_interval(geo_layer, field, class_count)
    else:
        raise ValueError(f'Unknow discretize method "{method}"')


def get_field_style(field):
    return ["get", field]


def get_style_no_value_condition(key, with_value, with_no_value):
    if with_no_value is not None:
        if with_value is not None:
            return [
                "case",
                ["==", ["typeof", key], "number"],
                with_value,
                with_no_value,
            ]
        else:
            return with_no_value
    else:
        return with_value


def gen_style_steps(expression, boundaries, colors):
    """
    Assume len(boundaries) <= len(colors) - 1
    """
    if len(boundaries) > 0:
        return ["step", expression, colors[0]] + _flatten(
            zip(boundaries[1:], colors[1:])
        )


def gen_legend_steps(boundaries, colors, no_value_color):
    """
    Generate a discrete legend.
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
            "shape": "square",
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
                "shape": "square",
            },
        )

    if not ret:
        ret = [DEFAULT_LEGEND_GRADUADED]

    return ret


def gen_style_interpolate(expression, boundaries, values):
    """
    Build a Mapbox GL Style interpolation expression.
    """
    return ["interpolate", ["linear"], expression] + _flatten(zip(boundaries, values))


def circle_boundaries_candidate(min, max):
    """
    Implementation of Self-Adjusting Legends for Proportional Symbol Maps
    https://pdfs.semanticscholar.org/d3f9/2bbd24ae83af6c101e5caacbd3e830d99272.pdf
    """
    if min is None or max is None:
        return []
    elif min <= 0:
        raise ValueError("Minimum value should be > 0")

    # array of base values in decreasing order in the range [1,10)
    bases = [5, 2.5, 1]
    # an index into the bases array
    base_id = 0
    # array that will hold the candidate values
    values = []
    # scale the minimum and maximum such that the minimum is > 1
    scale = 1  # scale factor
    min_s = min  # scaled minimum
    max_s = max  # scaled maximum
    while min_s < 1:
        min_s *= 10
        max_s *= 10
        scale /= 10

    # Compute the number of digits of the integral part of the scaled maximum
    ndigits = math.floor(math.log10(max_s))

    # Find the index into the bases array for the first limit smaller than max_s
    for i in range(0, len(bases)):
        if (max_s / 10 ** ndigits) >= bases[i]:
            base_id = i
            break

    while True:
        v = bases[base_id] * (10 ** ndigits)
        # stop the loop if the value is smaller than min_s
        if v <= min_s:
            break

        # otherwise store v in the values array
        values.append(
            v * scale
        )  # The the paper is false here, need mutiplication, no division
        # switch to the next base
        base_id += 1
        if base_id == len(bases):
            base_id = 0
            ndigits = ndigits - 1

    return values


def circle_boundaries_value_to_symbol_height(value, max_value, max_size):
    return math.sqrt(value / math.pi) * (max_size / math.sqrt(max_value / math.pi))


def circle_boundaries_filter_values(values, max_value, max_size, dmin):
    if not values or max_value is None or max_size is None:
        return []

    # array that will hold the filtered values
    filtered_values = []
    # add the maximum value
    filtered_values.append(values[0])
    # remember the height of the previously added value
    previous_height = circle_boundaries_value_to_symbol_height(
        values[0], max_value, max_size
    )
    # find the height and value of the smallest acceptable symbol
    last_height = 0
    last_value_id = len(values) - 1
    while last_value_id >= 0:
        last_height = circle_boundaries_value_to_symbol_height(
            values[last_value_id], max_value, max_size
        )
        if last_height > dmin:
            break
        last_value_id -= 1

    # loop over all values that are large enough
    for limit_id in range(1, last_value_id + 1):
        v = values[limit_id - 1]
        # compute the height of the symbol
        h = circle_boundaries_value_to_symbol_height(v, max_value, max_size)
        # do not draw the symbol if it is too close to the smallest symbol (but is not the smallest limit itself)
        if h - last_height < dmin and limit_id != last_value_id:
            continue
        # do not draw the symbol if it is too close to the previously drawn symbol
        if previous_height - h < dmin:
            continue
        filtered_values.append(v)
        # remember the height of the last drawn symbol
        previous_height = h

    return filtered_values


def lost_scale_digit(n, scale):
    """
    Return the number of digit to round
    """
    if n == 0:
        return 1  # Further in compuration 0 dived by 1 will be ok: 0
    else:
        return math.trunc(math.log10(n)) + 1 - scale


def trunc_scale(n, scale):
    lost = lost_scale_digit(n, scale)
    return math.trunc(n / (10 ** lost)) * (10 ** lost)


def round_scale(n, scale):
    lost = lost_scale_digit(n, scale)
    return round(n / (10 ** lost)) * (10 ** lost)


def ceil_scale(n, scale):
    lost = lost_scale_digit(n, scale)
    return math.ceil(n / (10 ** lost)) * (10 ** lost)


def boundaries_round(boundaries, scale=2):
    """
    Round boundaries to human readable number
    """
    return (
        [trunc_scale(boundaries[0], scale)]
        + [round_scale(b, scale) for b in boundaries[1:-2]]
        + [ceil_scale(boundaries[-1], scale)]
    )


def gen_legend_circle(
    min,
    max,
    size,
    color,
    no_value_circle_radius,
    no_value_color,
):
    """
    Generate a circle legend.
    """
    candidates = circle_boundaries_candidate(min, max)
    candidates = [max] + candidates + [min]
    boundaries = circle_boundaries_filter_values(
        candidates, max, size, DEFAULT_CIRCLE_MIN_LEGEND_HEIGHT
    )

    r = size / math.sqrt(max / math.pi)
    ret = [
        {
            "diameter": math.sqrt(b / math.pi) * r,
            "boundaries": {"lower": {"value": b}},
            "shape": "circle",
            "color": color,
        }
        for b in boundaries
    ]

    if no_value_circle_radius:
        ret.append(
            {
                "diameter": no_value_circle_radius * 2,
                "boundaries": {"lower": {"value": None}},
                "shape": "circle",
                "color": no_value_color,
            }
        )

    return ret


def gen_layer_color_graduation_style(
    field_getter,
    variable_field,
    color_graduation,
    style,
    style_no_value,
):
    """
    Build a Mapbox GL Style layer for color graduation.
    """
    mapbox_type = variable_field.split("_")[0]

    mapbox_style = {}

    for style_field, value in style.items():
        mapbox_style_field = style_field.replace("_", "-")

        if style_field == variable_field:
            style_value = color_graduation
        else:
            style_value = value if color_graduation else None

        val = get_style_no_value_condition(
            field_getter,
            style_value,
            style_no_value.get(style_field),
        )
        if val is not None:
            mapbox_style[mapbox_style_field] = val

    return {"type": mapbox_type, "paint": mapbox_style}


def gen_layer_proportionnal_value_style(
    proportionnal_value,
    sort_key,
    variable_field,
    style,
    style_no_value,
):
    """
    Build a Mapbox GL Style layer for color graduation.
    """
    mapbox_type = variable_field.split("_")[0]

    mapbox_style = {}

    for style_field, value in style.items():
        mapbox_style_field = style_field.replace("_", "-")

        if style_field == variable_field:
            style_value = proportionnal_value
        else:
            style_value = value

        mapbox_style[mapbox_style_field] = get_style_no_value_condition(
            proportionnal_value,
            style_value,
            style_no_value.get(style_field),
        )

    return {
        "type": mapbox_type,
        "layout": {f"{mapbox_type}-sort-key": ["-", sort_key]},
        "paint": mapbox_style,
    }


def generate_style_from_wizard(layer, config):
    """
    Return a Mapbox GL Style and a Legend from a wizard setting.
    """
    geo_layer = layer.source.get_layer()
    symbology = config["symbology"]

    if symbology == "graduated":
        # config["variable_field"] = "fill_color"
        return gen_graduated_color_style(geo_layer, config)
    elif symbology == "circle":
        # config["variable_field"] = "circle_radius"
        return gen_proportional_value_style(geo_layer, config)
    else:
        raise ValueError(f'Unknow symbology "{symbology}"')


def gen_graduated_color_style(geo_layer, config):
    """config = {
        "field": "my_field",
        "symbology": "graduated",
        "boundaries": [1, 2, 3, 5],
        "method": "equal_interval",  # How to compute boundaries if not provided
        "variable_field": "fill_color", # Style field to variate
        "style": {
            "fill_color": ["#ff0000", "#aa0000", "#770000", "#330000", "#000000"],
            "fill_opacity": 0.5,
            "fill_outline_color": "#ffffff",
        },
        "no_value_style": {
            "fill_color": "#000000",
            "fill_opacity": 0,
            "fill_outline_color": "#ffffff",
        },
    }
    """
    data_field = config["field"]
    variable_field = config["variable_field"]

    colors = config["style"].get(variable_field) if "style" in config else None

    # Step 1 generate boundaries
    if "boundaries" in config:
        boundaries = config["boundaries"]
        if len(boundaries) < 2:
            raise ValueError('"boundaries" must be at least a list of two values')
    elif "method" in config:
        boundaries = discretize(geo_layer, data_field, config["method"], len(colors))
    else:
        raise ValueError(
            'With "graduated" symbology, "boundaries" or "method" should be provided'
        )

    # Use boundaries to make style and legend
    if boundaries is not None:
        config_style = config.get("style", {})
        config_style_no_value = config.get("no_value_style", {})

        field_getter = ["get", data_field]

        style_steps = gen_style_steps(field_getter, boundaries, colors)

        style = gen_layer_color_graduation_style(
            field_getter,
            variable_field,
            color_graduation=style_steps,
            style=config_style,
            style_no_value=config_style_no_value,
        )

        legend_addition = {
            "items": gen_legend_steps(
                boundaries,
                colors,
                config_style_no_value.get(variable_field),
            )[::-1],
        }
        return (style, legend_addition)
    else:
        # Generate default style if no value
        default_style = {"type": variable_field.split("_")[0]}
        default_style["paint"] = config["style"]
        default_style["paint"][variable_field] = config["style"][variable_field][0]
        # Update no_value_style
        default_style["paint"].update(config.get("no_value_style", {}))
        # Rename properties for mapbox
        default_style["paint"] = {
            k.replace("_", "-"): v for (k, v) in default_style["paint"].items()
        }
        return (
            default_style,
            {"items": [DEFAULT_LEGEND_GRADUADED]},
        )


def gen_proportional_value_style(geo_layer, config):
    """config = {
        "field": "my_field",
        "symbology": "circle",
        "max_diameter": 200,
        "style": {
            "circle_color": "#0000cc",
            "circle_opacity": 0.5,
            "circle_stroke_color": "#ffffff",
            "circle_stroke_width": 1,
        },
        "no_value_style": { # Specify no_value style if any
            "circle_color": "#000000",
            "circle_opacity": 0,
            "circle_stroke_color": "#ffffff",
            "circle_stroke_width": 1,
        },
    }
    """
    data_field = config["field"]
    proportional_field = config["variable_field"]

    field_getter = ["get", config["field"]]

    mm = get_positive_min_max(geo_layer, data_field)
    if mm[1] is not None and mm[2] is not None:
        mm = boundaries_round(mm[1:])
        boundaries = [0, math.sqrt(mm[1] / math.pi)]
        sizes = [0, config["max_value"] / 2]

        radius_base = ["sqrt", ["/", field_getter, ["pi"]]]
        radius = gen_style_interpolate(radius_base, boundaries, sizes)

        config_style = config["style"]
        config_style[proportional_field] = radius
        config_style_no_value = config.get("no_value_style", {})

        style = gen_layer_proportionnal_value_style(
            proportionnal_value=radius,
            sort_key=field_getter,
            variable_field=proportional_field,
            style=config_style,
            style_no_value=config_style_no_value,
        )

        legend_addition = {
            "items": gen_legend_circle(
                mm[0],
                mm[1],
                config["max_value"],
                config_style["circle_color"],
                config_style_no_value.get(proportional_field),
                config_style_no_value.get("circle_color"),
            ),
            "stackedCircles": True,
        }
        return (style, legend_addition)
    else:
        # Generate default style if no value
        default_style = {"type": proportional_field.split("_")[0]}
        default_style["paint"] = config["style"]
        default_style["paint"][proportional_field] = config["max_value"]
        # Update no_value_style
        default_style["paint"].update(config.get("no_value_style", {}))
        # Rename properties for mapbox
        default_style["paint"] = {
            k.replace("_", "-"): v for (k, v) in default_style["paint"].items()
        }
        return (
            default_style,
            {"items": [DEFAULT_LEGEND_CIRCLE]} if config.get("no_value_style") else {},
        )