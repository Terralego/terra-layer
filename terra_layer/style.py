from django.db import connection
import numbers
import math
from functools import reduce

DEFAULT_FILL_COLOR = '#0000cc'
DEFAULT_STROKE_COLOR = '#ffffff'


def _flatten(l):
    """
    Flatten 2-level array.
    [[1,2], [3, 4, 5]] -> [1, 2, 3, 4, 5]
    """
    return list(reduce(lambda x, y: x + y, l))


def get_min_max(geo_layer, property):
    """
    Return the max and the min value of a property.
    """
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT
                min((properties->>%(property)s)::numeric) AS min, -----------------------------
                max((properties->>%(property)s)::numeric) AS max -----------------------------
            FROM
                geostore_feature
            WHERE
                layer_id = %(layer_id)s
            ''', {
            'property': property,
            'layer_id': geo_layer.id
        })
        row = cursor.fetchone()
        if row:
            min, max = row
            return [min, max]
        else:
            return [None, None]


def get_positive_min_max(geo_layer, property):
    """
    Return the max and the min value of a property.
    """
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT
                min((properties->>%(property)s)::numeric) AS min, -----------------------------
                max((properties->>%(property)s)::numeric) AS max -----------------------------
            FROM
                geostore_feature
            WHERE
                layer_id = %(layer_id)s AND
                (properties->>%(property)s)::numeric > 0
            ''', {
            'property': property,
            'layer_id': geo_layer.id
        })
        row = cursor.fetchone()
        if row:
            min, max = row
            return [min, max]
        else:
            return [None, None]


def discretize_quantile(geo_layer, property, class_count):
    """
    Compute Quantile class boundaries from a layer property.
    """
    with connection.cursor() as cursor:
        cursor.execute('''
            WITH
            ntiles AS (
                SELECT
                    (properties->>%(property)s)::numeric AS value,
                    ntile(%(class_count)s) OVER (ORDER BY (properties->>%(property)s)::numeric) AS ntile
                FROM
                    geostore_feature
                WHERE
                    layer_id = %(layer_id)s
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
            ''', {
            'property': property,
            'class_count': class_count,
            'layer_id': geo_layer.id,
        })
        rows = cursor.fetchall()
        if rows:
            # Each class start + last class end
            return [r[0] for r in rows] + [rows[-1][1]]
        else:
            return [0 + 1 * i for i in range(0, class_count)]


def discretize_jenks(geo_layer, property, class_count):
    """
    Compute Jenks class boundaries from a layer property.
    Note: Use PostGIS ST_ClusterKMeans() as k-means function.
    """
    with connection.cursor() as cursor:
        cursor.execute('''
            WITH
            kmeans AS (
                SELECT
                    (properties->>%(property)s)::numeric AS property,
                    ST_ClusterKMeans(
                        ST_MakePoint((properties->>%(property)s)::numeric, 0),
                        least(%(class_count)s, (SELECT count(*) FROM geostore_feature WHERE layer_id = %(layer_id)s))::integer
                    ) OVER () AS class_id
                FROM
                    geostore_feature
                WHERE
                    layer_id = %(layer_id)s
            )
            SELECT
                min(property) AS min,
                max(property) AS max
            FROM
                kmeans
            GROUP BY
                class_id
            ORDER BY
                min,
                max
            ''', {
            'property': property,
            'class_count': class_count,
            'layer_id': geo_layer.id,
        })
        rows = cursor.fetchall()
        if rows:
            # # Each class start + last class end
            return [r[0] for r in rows] + [rows[-1][1]]
        else:
            return [0 + 1 * i for i in range(0, class_count)]


def discretize_equal_interval(geo_layer, property, class_count):
    """
    Compute QuantiEqual Interval class boundaries from a layer property.
    """
    min, max = get_min_max(geo_layer, property)
    if min is not None and max is not None and isinstance(min, numbers.Number):
        delta = (max - min) / class_count
        return [min + delta * i for i in range(0, class_count + 1)]
    else:
        return [0 + 1 * i for i in range(0, class_count)]


def discretize(geo_layer, property, method, class_count):
    """
    Select a method to compute class boundaries.
    Compute (len(class_count) + 1) boundaries.
    Note, can returns less boundaries than requested if lesser values in property than class_count
    """
    if method == 'quantile':
        return discretize_quantile(geo_layer, property, class_count)
    elif method == 'jenks':
        return discretize_jenks(geo_layer, property, class_count)
    elif method == 'equal_interval':
        return discretize_equal_interval(geo_layer, property, class_count)
    else:
        raise ValueError(f'Unknow discretize method "{method}"')


def get_property_style(property):
    return ['get', property]


def gen_style_steps(expression, boundaries, colors):
    """
    Assume len(boundaries) <= len(colors) - 1
    """
    return [
        'step',
        expression,
        colors[0]
    ] + _flatten(zip(boundaries[1:], colors[1:]))


def gen_legend_steps(boundaries, colors):
    """
    Generate a discrete legend.
    """
    size = len(boundaries) - 1
    return [{
        'color': colors[index],
        'label': f'[{boundaries[index]} – {boundaries[index+1]}' + (']' if index + 1 == size else ')'),
        'shape': 'square',
    } for index in range(size)]


def gen_style_interpolate(expression, boundaries, values):
    """
    Build a Mapbox GL Style interpolation expression.
    """
    return [
        'interpolate', 'linear',
        expression
    ] + _flatten(zip(boundaries, values))


# Implementation of Self-Adjusting Legends for Proportional Symbol Maps
# https://pdfs.semanticscholar.org/d3f9/2bbd24ae83af6c101e5caacbd3e830d99272.pdf

def circle_boundaries_candidate(min, max):
    if min == 0:
        raise ValueError('Minimum value should be > 0')

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
        if (max_s / 10**ndigits) >= bases[i]:
            base_id = i
            break

    while True:
        v = bases[base_id] * (10 ** ndigits)
        # stop the loop if the value is smaller than min_s
        if (v <= min_s):
            break

        # otherwise store v in the values array
        values.append(v / scale)
        # switch to the next base
        base_id += 1
        if base_id == len(bases):
            base_id = 0
            ndigits = ndigits - 1

    return values


def circle_boundaries_value_to_symbol_height(value, max_value, max_size):
    return 2 * math.sqrt(value * max_size / max_value / math.pi)


def circle_boundaries_filter_values(values, max_value, max_size, dmin):
    # array that will hold the filtered values
    filtered_values = []
    # add the maximum value
    filtered_values.append(values[0])
    # remember the height of the previously added value
    previous_height = circle_boundaries_value_to_symbol_height(values[0], max_value, max_size)
    # find the height and value of the smallest acceptable symbol
    last_height = 0
    last_value_id = len(values) - 1
    while last_value_id >= 0:
        last_height = circle_boundaries_value_to_symbol_height(values[last_value_id], max_value, max_size)
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


def gen_legend_circle(min, max, size):
    """
    Generate a circle legend.
    """
    candidates = circle_boundaries_candidate(min, max)
    candidates = [max] + candidates + [min]
    boundaries = circle_boundaries_filter_values(candidates, min, max, size / 20)[::-1]
    return [{
        'radius': b * size / max,
        'label': f'{b}',
        'shape': 'circle',
    } for b in boundaries]


def gen_layer_fill(fill_color=DEFAULT_FILL_COLOR, stroke_color=DEFAULT_STROKE_COLOR):
    """
    Build a Mapbox GL Style layer for pylygon fill.
    """
    return {
        'type': 'fill',
        'paint': {
            'fill-color': fill_color,
            'fill-outline-color': stroke_color,
        }
    }


def gen_layer_circle(radius, fill_color=DEFAULT_FILL_COLOR, stroke_color=DEFAULT_STROKE_COLOR):
    """
    Build a Mapbox GL Style layer for circle.
    """
    return {
        'type': 'circle',
        'paint': {
            'circle-radius': radius,
            'circle-stroke-color': stroke_color,
        }
    }


def generate_style_from_wizard(layer, config):
    """
    Return a Mapbox GL Style and a Legend from a wizard setting.
    """
    geo_layer = layer.source.get_layer()
    symbology = config['symbology']
    property = config['property']

    if symbology == 'graduated':
        # {
        #     "property": "my_property",
        #     "symbology": "graduated",
        #     "method": "equal_interval",
        #     "fill_color": ["#ff0000", "#aa0000", "#770000", "#330000", "#000000"],
        #     "stroke_color": "#ffffff",
        # }
        colors = config['fill_color']
        boundaries = discretize(geo_layer, property, config['method'], len(colors))
        style = gen_layer_fill(
            fill_color=gen_style_steps(get_property_style(property), boundaries, colors),
            stroke_color=config.get('stroke_color', DEFAULT_STROKE_COLOR),
        )
        legend = gen_legend_steps(boundaries, colors)
        return {'style': style, 'legend': legend}

    elif symbology == 'circle':
        # {
        #    "property": "my_property",
        #     "symbology": "circle",
        #     "max_diameter": 200,
        #     "fill_color": "#0000cc",
        #     "stroke_color": "#ffffff",
        # }
        mm = get_positive_min_max(geo_layer, property)
        boundaries = [0, mm[1]]
        sizes = [0, config['max_diameter']]
        radius = ['sqrt', ['/', get_property_style(property), ['pi']]]
        style = gen_layer_circle(
            radius=gen_style_interpolate(radius, boundaries, sizes),
            fill_color=config.get('fill_color', DEFAULT_FILL_COLOR),
            stroke_color=config.get('stroke_color', DEFAULT_STROKE_COLOR),
        )
        legend = gen_legend_circle(mm[0], mm[1], sizes[1])
        return {'style': style, 'legend': legend}

    else:
        raise ValueError(f'Unknow symbology "{symbology}"')
