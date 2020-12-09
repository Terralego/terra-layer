# Generated by Django 2.2.17 on 2020-11-30 08:28

from django.db import migrations, transaction


def fill_style_name(field):
    if field == "stroke_color":
        return "fill_outline_color"
    else:
        return field


def circle_style_name(field):
    if field == "stroke_color":
        return "circle_stroke_color"
    elif field == "stroke_width":
        return "circle_stroke_width"
    elif field == "fill_opacity":
        return "circle_opacity"
    else:
        return field


def migrate_graduated_wizard(layer):
    field = layer.layer_style_wizard["field"]
    method = layer.layer_style_wizard.get("method")
    boundaries = layer.layer_style_wizard.get("boundaries")
    fill_colors = layer.layer_style_wizard["style"]["fill_color"]

    # Other fields
    fields = {}
    no_value_fields = {}

    for f in ["fill_color", "fill_opacity", "stroke_color"]:
        fields[f] = layer.layer_style_wizard["style"].get(f)
        no_value_fields[f] = layer.layer_style_wizard.get("no_value_style", {}).get(f)

    layer.main_style = {
        "type": "wizard",
        "map_style_type": "fill",
        "style": {
            "fill_color": {
                "type": "variable",
                "field": field,
                "values": fill_colors,
            },
        },
    }
    if boundaries:
        layer.main_style["style"]["fill_color"]["boundaries"] = boundaries
    if method:
        layer.main_style["style"]["fill_color"]["method"] = method
    if no_value_fields["fill_color"]:
        layer.main_style["style"]["fill_color"]["no_value"] = no_value_fields[
            "fill_color"
        ]

    del fields["fill_color"]

    for field, value in fields.items():
        if value:
            layer.main_style["style"][fill_style_name(field)] = {
                "type": "fixed",
                "value": value,
            }
            if fields[field]:
                layer.main_style["style"][fill_style_name(field)]["no_value"] = fields[
                    field
                ]


def migrate_circle_wizard(layer):
    field = layer.layer_style_wizard["field"]
    max_diameter = layer.layer_style_wizard["max_diameter"]
    fields = {}
    no_value_fields = {}

    for f in [
        "circle_radius",
        "fill_color",
        "fill_opacity",
        "stroke_color",
        "stroke_width",
    ]:
        fields[f] = layer.layer_style_wizard["style"].get(f)
        no_value_fields[f] = layer.layer_style_wizard.get("no_value_style", {}).get(f)

    layer.main_style = {
        "type": "wizard",
        "map_style_type": "circle",
        "style": {
            "circle_radius": {
                "type": "variable",
                "field": field,
                "max_radius": max_diameter,
            },
        },
    }

    if no_value_fields["circle_radius"]:
        layer.main_style["style"]["circle_radius"]["no_value"] = no_value_fields[
            "circle_radius"
        ]

    del fields["circle_radius"]

    for field, value in fields.items():
        if value:
            layer.main_style["style"][circle_style_name(field)] = {
                "type": "fixed",
                "value": value,
            }
            if fields[field]:
                layer.main_style["style"][circle_style_name(field)][
                    "no_value"
                ] = fields[field]


@transaction.atomic
def forward(apps, schema_editor):
    Layer = apps.get_model("terra_layer", "Layer")

    for layer in Layer.objects.all():
        if layer.main_style:
            print(f"Nothing to do for {layer}. Already migrated ?")
            continue

        if layer.layer_style_wizard:
            print(f"Wizard style for {layer}")
            if layer.layer_style_wizard["symbology"] == "graduated":
                migrate_graduated_wizard(layer)
            elif layer.layer_style_wizard["symbology"] == "circle":
                migrate_graduated_wizard(layer)
        elif layer.layer_style:
            print(f"Advanced style for {layer}")
            layer.main_style = {
                "type": "advanced",
                "map_style_type": layer.layer_style["type"],
            }
        else:
            print(f"No style found for layer {layer}")

        # Keep previously generated style
        layer.main_style["map_style"] = layer.layer_style
        layer.save()

        # Migrate extra styles
        for extra in layer.extra_styles.all():
            if extra.style:
                extra.style_config = {
                    "type": "advanced",
                    "map_style_type": extra.style.get(
                        "type",
                        list(extra.style.get("paint", {"fill-color": ""}).keys())[
                            0
                        ].split("-")[0],
                    ),
                    "map_style": extra.style,
                }
                extra.save()


def backward(apps, schema_editor):
    Layer = apps.get_model("terra_layer", "Layer")

    for layer in Layer.objects.all():
        layer.layer_style = layer.main_style["map_style"]
        # Here we loose the wizard. Too hard to migrate.
        layer.save()


class Migration(migrations.Migration):

    dependencies = [
        ("terra_layer", "0057_add_new_style_field"),
    ]

    operations = [
        migrations.RunPython(forward, reverse_code=backward),
    ]
