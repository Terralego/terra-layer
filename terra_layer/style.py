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


def min_max(geo_layer, property):
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


def discretize_quantile(geo_layer, property, class_number):
    with connection.cursor() as cursor:
        cursor.execute('''
            WITH
            ntiles AS (
                SELECT
                    (properties->>%(property)s)::numeric AS value,
                    ntile(%(class_number)s) OVER (ORDER BY (properties->>%(property)s)::numeric) AS ntile
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
            'class_number': class_number,
            'layer_id': geo_layer.id,
        })
        rows = cursor.fetchall()
        if rows:
            return list(map(lambda r: r[0], rows)) + [rows[-1][1]]
        else:
            return [0 + 1 * i for i in range(0, class_number)]


def discretize_jenks(geo_layer, property, class_number):
    with connection.cursor() as cursor:
        cursor.execute('''
            WITH
            kmeans AS (
                SELECT
                    (properties->>%(property)s)::numeric AS property,
                    ST_ClusterKMeans(
                        ST_MakePoint((properties->>%(property)s)::numeric, 0),
                        least(%(class_number)s, (SELECT count(*) FROM geostore_feature WHERE layer_id = %(layer_id)s))::integer
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
            'class_number': class_number,
            'layer_id': geo_layer.id,
        })
        rows = cursor.fetchall()
        if rows:
            return list(map(lambda r: r[0], rows)) + [rows[-1][1]]
        else:
            return [0 + 1 * i for i in range(0, class_number)]


def discretize_equal_interval(geo_layer, property, class_number):
    min, max = min_max(geo_layer, property)
    if min is not None and max is not None and isinstance(min, numbers.Number):
        delta = (max - min) / class_number
        return [min + delta * i for i in range(0, class_number + 1)]
    else:
        return [0 + 1 * i for i in range(0, class_number)]


def discretize(geo_layer, property, method, class_number):
    if method == 'quantile':
        return discretize_quantile(geo_layer, property, class_number)
    elif method == 'jenks':
        return discretize_jenks(geo_layer, property, class_number)
    elif method == 'equal_interval':
        return discretize_equal_interval(geo_layer, property, class_number)
    else:
        raise ValueError(f'Unknow discretize method "{method}"')


def steps_style(property, boundaries, colors):
    """
    Assume len(boundaries) <= len(colors) - 1
    """
    return [
        'step',
        ['get', property],
        colors[0]
    ] + _flatten(zip(boundaries[1:], colors[1:]))


def steps_legend(boundaries, colors):
    size = len(boundaries)
    return list(map(lambda index: {
        'color': colors[index],
        'label': f'[{boundaries[index]} – {boundaries[index+1]}' + (']' if index + 1 == size - 1 else ')'),
        'shape': 'square',
    }, range(0, size - 1)))


def interpolate_style(property, boundaries, values):
    return [
        'interpolate', 'linear',
        ['get', property]
    ] + _flatten(zip(boundaries, values))


def circle_legend(boundaries, sizes):
    return list(map(lambda bs: {
        'radius': bs[1],
        'label': f'{bs[0]}',
        'shape': 'circle',
    }, zip(boundaries, sizes)))


def layer_fill(fill_color=DEFAULT_FILL_COLOR, stroke_color=DEFAULT_STROKE_COLOR):
    return {
        'type': 'fill',
        'paint': {
            'fill-color': fill_color,
            'fill-outline-color': stroke_color,
        }
    }


def layer_circle(radius, fill_color=DEFAULT_FILL_COLOR, stroke_color=DEFAULT_STROKE_COLOR):
    return {
        'type': 'circle',
        'paint': {
            'circle-radius': radius,
            'circle-stroke-color': stroke_color,
        }
    }


def generator(layer, config):
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
        style = layer_fill(
            fill_color=steps_style(property, boundaries, colors),
            stroke_color=config.get('stroke_color', DEFAULT_STROKE_COLOR),
        )
        legend = steps_legend(boundaries, colors)
        return {'style': style, 'legend': legend}

    elif symbology == 'circle':
        # {
        #    "property": "my_property",
        #     "symbology": "circle",
        #     "max_diameter": 200,
        #     "fill_color": "#0000cc",
        #     "stroke_color": "#ffffff",
        # }
        boundaries = [0, min_max(geo_layer, property)[1]]
        sizes = [0, config['max_diameter']]
        style = layer_circle(
            radius=interpolate_style(property, boundaries, sizes),
            fill_color=config.get('fill_color', DEFAULT_FILL_COLOR),
            stroke_color=config.get('stroke_color', DEFAULT_STROKE_COLOR),
        )
        legend = circle_legend(boundaries, sizes)
        return {'style': style, 'legend': legend}

    else:
        raise ValueError(f'Unknow symbology "{symbology}"')
