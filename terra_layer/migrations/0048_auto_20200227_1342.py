# Generated by Django 3.0.3 on 2020-02-27 13:42

import django.contrib.postgres.fields.jsonb
from django.db import migrations
import terra_layer.schema


class Migration(migrations.Migration):

    dependencies = [
        ("terra_layer", "0047_add_uuid"),
    ]

    operations = [
        migrations.AddField(
            model_name="layer",
            name="layer_style_wizard",
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name="scene",
            name="tree",
            field=django.contrib.postgres.fields.jsonb.JSONField(
                default=list,
                validators=[
                    terra_layer.schema.JSONSchemaValidator(
                        limit_value={
                            "$id": "http://terralego.com/scene_layertree.json",
                            "$schema": "http://json-schema.org/draft-07/schema#",
                            "definitions": {},
                            "items": {
                                "$id": "#/items",
                                "dependencies": {"group": ["children", "label"]},
                                "properties": {
                                    "children": {"$ref": "#"},
                                    "expanded": {
                                        "$id": "#/items/properties/expanded",
                                        "default": False,
                                        "examples": [True],
                                        "title": "The expanded status in admin. Not used yet",
                                        "type": "boolean",
                                    },
                                    "geolayer": {
                                        "$id": "#/items/properties/geolayer",
                                        "default": 0,
                                        "examples": [96],
                                        "title": "The geolayer id",
                                        "type": "integer",
                                    },
                                    "group": {
                                        "$id": "#/items/properties/group",
                                        "default": False,
                                        "examples": [True],
                                        "title": "The group name. Present if it's a group.",
                                        "type": "boolean",
                                    },
                                    "label": {
                                        "$id": "#/items/properties/label",
                                        "default": "",
                                        "examples": ["My Group"],
                                        "pattern": "^(.*)$",
                                        "title": "The group name",
                                        "type": "string",
                                    },
                                    "selectors": {
                                        "$id": "#/items/properties/selectors",
                                        "title": "The selectors for this group",
                                        "type": ["array", "null"],
                                    },
                                    "settings": {
                                        "$id": "#/items/properties/settings",
                                        "title": "The settings of group",
                                        "type": "object",
                                    },
                                },
                                "required": [],
                                "title": "Layer tree item",
                                "type": "object",
                            },
                            "title": "Scene layer tree schema",
                            "type": "array",
                        }
                    )
                ],
            ),
        ),
    ]
