from django.db import connection
import numbers
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


def gen_style_steps(property, boundaries, colors):
    """
    Assume len(boundaries) <= len(colors) - 1
    """
    return [
        'step',
        ['get', property],
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


def gen_style_interpolate(property, boundaries, values):
    """
    Build a Mapbox GL Style interpolation expression.
    """
    return [
        'interpolate', 'linear',
        ['get', property]
    ] + _flatten(zip(boundaries, values))


def gen_legend_circle(boundaries, sizes):
    """
    Generate a circle legend.
    """
    return [{
        'radius': s,
        'label': f'{b}',
        'shape': 'circle',
    } for b, s in zip(boundaries, sizes)]


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
            fill_color=gen_style_steps(property, boundaries, colors),
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
        boundaries = [0, get_min_max(geo_layer, property)[1]]
        sizes = [0, config['max_diameter']]
        style = gen_layer_circle(
            radius=gen_style_interpolate(property, boundaries, sizes),
            fill_color=config.get('fill_color', DEFAULT_FILL_COLOR),
            stroke_color=config.get('stroke_color', DEFAULT_STROKE_COLOR),
        )
        legend = gen_legend_circle(boundaries, sizes)
        return {'style': style, 'legend': legend}

    else:
        raise ValueError(f'Unknow symbology "{symbology}"')
