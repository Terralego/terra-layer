from django.conf import settings

# Min height between circle legend labels, in pixels. Typically based on label police size.
STYLE_CIRCLE_MIN_LEGEND_HEIGHT = getattr(settings, "STYLE_CIRCLE_MIN_LEGEND_HEIGHT", 14)
