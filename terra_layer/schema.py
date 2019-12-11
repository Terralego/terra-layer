"""
All json schema for validation
"""

import django
from django.core.validators import BaseValidator
import jsonschema


class JSONSchemaValidator(BaseValidator):
    def compare(self, a, b):
        try:
            jsonschema.validate(a, b)
        except jsonschema.exceptions.ValidationError as e:
            raise django.core.exceptions.ValidationError(
                "%(value)s failed JSON schema check", params={"value": a}
            )


SCENE_LAYERTREE = {
    "definitions": {},
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "http://terralego.com/scene_layertree.json",
    "type": "array",
    "title": "Scene layer tree schema",
    "items": {
        "$id": "#/items",
        "type": "object",
        "title": "Layer tree item",
        "required": [],
        "dependencies": {"group": ["children", "title"]},
        "properties": {
            "title": {
                "$id": "#/items/properties/title",
                "type": "string",
                "title": "The group name",
                "default": "",
                "examples": ["My Group"],
                "pattern": "^(.*)$",
            },
            "expanded": {
                "$id": "#/items/properties/expanded",
                "type": "boolean",
                "title": "The expanded status in admin. Not used yet",
                "default": False,
                "examples": [True],
            },
            "geolayer": {
                "$id": "#/items/properties/geolayer",
                "type": "integer",
                "title": "The geolayer id",
                "default": 0,
                "examples": [96],
            },
            "group": {
                "$id": "#/items/properties/group",
                "type": "boolean",
                "title": "The group name. Present if it's a group.",
                "default": False,
                "examples": [True],
            },
            "children": {"$ref": "#"},
        },
    },
}
