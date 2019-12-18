# Generated by Django 2.2.7 on 2019-12-12 10:29

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import terra_layer.schema


class Migration(migrations.Migration):

    dependencies = [
        ("terra_layer", "0044_order"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="layer", options={"ordering": ("order", "name")},
        ),
        migrations.AddField(
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
        migrations.AlterField(
            model_name="layer",
            name="group",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="layers",
                to="terra_layer.LayerGroup",
            ),
        ),
        migrations.AlterUniqueTogether(name="layergroup", unique_together=set(),),
    ]
