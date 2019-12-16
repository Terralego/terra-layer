# Generated by Django 2.2.7 on 2019-12-12 10:29

from django.db import migrations, transaction


def layer2dict(layer):
    return {"geolayer": layer.id, "label": layer.name}


def group2dict(group):
    children = []

    for sub_group in group.children.all():
        children.append(group2dict(sub_group))

    for sub_layer in group.layers.all():
        children.append(layer2dict(sub_layer))

    return {
        "label": group.label,
        "group": True,
        "children": children,
        "exclusive": group.exclusive,
        "selectors": group.selectors,
        "settings": group.settings,
    }


@transaction.atomic
def group2scene_tree(apps, schema_editor):
    Scene = apps.get_model("terra_layer", "Scene")
    LayerGroup = apps.get_model("terra_layer", "LayerGroup")
    Layer = apps.get_model("terra_layer", "Layer")

    def tree2models(scene, current_node, parent=None, order=0):
        """
        Copied and adapted from the one in `models.py` to avoid further evolutions.
        """

        if not parent:
            # Create a default unique parent group that is ignored at export
            parent = LayerGroup.objects.create(view=scene, label="Root")

        if isinstance(current_node, list):
            for idx, child in enumerate(current_node):
                tree2models(scene, current_node=child, parent=parent, order=idx)

        elif "group" in current_node:
            # Handle groups
            group = parent.children.create(
                view=scene,
                label=current_node["label"],
                exclusive=current_node.get("exclusive", False),
                order=order,
            )

            if "children" in current_node:
                tree2models(scene, current_node=current_node["children"], parent=group)

        elif "geolayer" in current_node:
            # Handle layers
            layer = Layer.objects.get(pk=current_node["geolayer"])
            layer.group = parent
            layer.order = order
            layer.save()

    for scene in Scene.objects.all():
        tree = []
        for lg in LayerGroup.objects.filter(view=scene, parent=None):
            tree.append(group2dict(lg))
        # There is no sublayer at level 0 so no need to handle them
        scene.tree = tree

        scene.save()
        scene.layer_groups.all().delete()  # Clear all groups to generate brand new one
        tree2models(scene, tree)


class Migration(migrations.Migration):

    dependencies = [
        ("terra_layer", "0045_add_tree_2_scene"),
    ]

    operations = [
        migrations.RunPython(group2scene_tree),
    ]
