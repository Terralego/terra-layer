from terra_layer.style.utils import (
    trunc_scale,
    get_min_max,
    circle_boundaries_candidate,
    round_scale,
    ceil_scale,
    circle_boundaries_filter_values,
)

from terra_layer.settings import (
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

from .color import (
    gen_graduated_color_legend,
    gen_graduated_color_style,
)

from .size import (
    gen_categorized_size_legend,
    gen_categorized_size_style,
    gen_graduated_size_legend,
    gen_graduated_size_style,
    gen_proportionnal_size_legend,
    gen_proportionnal_size_style,
)

from .radius import (
    gen_proportionnal_radius_legend,
    gen_proportionnal_radius_style,
)


def to_map_style(prop):
    return prop.replace("_", "-")


def field_2_variation_type(field):
    if "color" in field:
        return "color"
    if "width" in field or "height" in field:
        return "value"
    if "radius" in field or "size" in field:
        return "radius"


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
                    map_style["paint"][map_style_prop] = gen_categorized_size_style(
                        geo_layer, data_field, prop_config, DEFAULT_NO_VALUE_FILL_COLOR
                    )
                    if map_style["paint"][map_style_prop] is None:
                        del map_style["paint"][map_style_prop]

                    if prop_config.get("generate_legend"):
                        legends.append(
                            gen_categorized_size_legend(
                                map_style_type,
                                prop_config,
                                "color",
                            )
                        )
                else:
                    raise ValueError(f'Unhandled analysis type "{analysis}"')

            if variation_type == "radius":
                if analysis == "categorized":
                    map_style["paint"][map_style_prop] = gen_categorized_size_style(
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
                            gen_categorized_size_legend(
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
                    map_style["paint"][map_style_prop] = gen_categorized_size_style(
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
                            gen_categorized_size_legend(
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
