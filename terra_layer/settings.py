from django.conf import settings

default_settings = getattr(settings, "TERRA_LAYER_STYLE_SETTINGS", {})

# Min height between circle legend labels, in pixels. Typically based on label police size.
DEFAULT_CIRCLE_MIN_LEGEND_HEIGHT = default_settings.get("circle_min_legend_height", 14)
DEFAULT_FILL_COLOR = default_settings.get("fill_color", "#0000cc")
DEFAULT_FILL_OPACITY = default_settings.get("fill_opacity", 0.4)
DEFAULT_STROKE_COLOR = default_settings.get("stroke_color", "#ffffff")
DEFAULT_STROKE_WIDTH = default_settings.get("stroke_width", 0.3)
