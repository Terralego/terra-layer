from django.db import connection
import numbers
import math
from functools import reduce
from terra_layer.settings import (
    DEFAULT_CIRCLE_MIN_LEGEND_HEIGHT,
    DEFAULT_SIZE_MIN_LEGEND_HEIGHT,
    DEFAULT_NO_VALUE_FILL_COLOR,
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


def gen_style_steps(expression, boundaries, values):
    """
    Assume len(boundaries) <= len(colors) - 1
    """
    if len(boundaries) > 0:
        return ["step", expression, values[0]] + _flatten(
            zip(boundaries[1:], values[1:])
        )


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


def gen_style_interpolate(expression, boundaries, values):
    """
    Build a Mapbox GL Style interpolation expression.
    """
    return ["interpolate", ["linear"], expression] + _flatten(zip(boundaries, values))


def size_boundaries_candidate(min, max):
    return [(max - min) / 2]


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
        if not map_field.replace('fill_extrusion', 'extrusion').startswith(map_style_type.replace("fill-extrusion", "extrusion")):
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
