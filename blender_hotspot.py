"""Apply a hotspot texture set to a mesh with DreamUV, inside a running Blender.

Run in Blender (e.g. through Blender MCP's execute_blender_code):

    import runpy
    hotspot = runpy.run_path("/path/to/material-maker-mcp/blender_hotspot.py")
    result = hotspot["apply_hotspot"]("Cube", "/path/to/hotspot-maps")

The maps directory must contain albedo.png, normal.png, and orm.png as written by
`mm-material convert-hotspot`. Pass names=... for other file names, e.g. devil/hotspot/devil_orm_*.png.

Requires the DreamUV add-on. On Blender 5.x, DreamUV's DUV_Utils.square_fit must call
mesh.select_edge_loop_multi instead of the removed mesh.loop_multi_select (see HOTSPOT_MATERIAL.md).
"""

import os

import bpy

ATLAS_BLEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hotspot_uv.blend")
ATLAS_NAME = "HotspotAtlas"


def ensure_atlas():
    """Append the reference plane whose faces define the atlas panels, hidden from viewport and render."""
    atlas = bpy.data.objects.get(ATLAS_NAME)
    if atlas:
        return atlas
    with bpy.data.libraries.load(ATLAS_BLEND, link=False) as (src, dst):
        dst.objects = ["Plane"]
    atlas = dst.objects[0]
    atlas.name = ATLAS_NAME
    coll = bpy.data.collections.new(ATLAS_NAME)
    bpy.context.scene.collection.children.link(coll)
    coll.objects.link(atlas)
    atlas.location = (0, 0, -5)
    atlas.hide_render = True
    atlas.hide_set(True)
    return atlas


def ensure_material(name, maps_dir, names):
    """Principled BSDF from albedo, OpenGL normal, and ORM (R = AO, G = roughness, B = metallic)."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]

    def image(key, non_color, y):
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(os.path.join(maps_dir, names[key]), check_existing=True)
        if non_color:
            node.image.colorspace_settings.name = "Non-Color"
        node.location = (-900, y)
        return node

    albedo = image("albedo", False, 300)
    orm = image("orm", True, 0)
    normal = image("normal", True, -300)
    split = nt.nodes.new("ShaderNodeSeparateColor")
    split.location = (-550, 0)
    normal_map = nt.nodes.new("ShaderNodeNormalMap")
    normal_map.location = (-550, -300)
    ao = nt.nodes.new("ShaderNodeMix")
    ao.data_type = "RGBA"
    ao.blend_type = "MULTIPLY"
    ao.inputs["Factor"].default_value = 1.0
    ao.location = (-350, 300)

    link = nt.links.new
    link(orm.outputs["Color"], split.inputs["Color"])
    link(albedo.outputs["Color"], ao.inputs["A"])
    link(split.outputs["Red"], ao.inputs["B"])
    link(ao.outputs["Result"], bsdf.inputs["Base Color"])
    link(split.outputs["Green"], bsdf.inputs["Roughness"])
    link(split.outputs["Blue"], bsdf.inputs["Metallic"])
    # Material Maker exports OpenGL normals, which is also Blender's convention.
    link(normal.outputs["Color"], normal_map.inputs["Color"])
    link(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def apply_hotspot(object_name, maps_dir, material_name="HotspotMetal", names=None):
    names = names or {"albedo": "albedo.png", "normal": "normal.png", "orm": "orm.png"}
    scene = bpy.context.scene
    obj = bpy.data.objects[object_name]
    scene.subrect_atlas1 = ensure_atlas()
    scene.duv_hotspotmaterial1 = ensure_material(material_name, maps_dir, names)
    scene.duv_hotspot_atlas1 = True

    win = bpy.context.window_manager.windows[0]
    area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
    region = next(r for r in area.regions if r.type == "WINDOW")
    with bpy.context.temp_override(window=win, area=area, region=region):
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        # Override only window/area/region: DreamUV edits a temporary duplicate, and pinning
        # `object` to the target breaks its edit-mode calls.
        try:
            ret = bpy.ops.view3d.dreamuv_hotspotter()
        finally:
            # A failed run leaves DreamUV's duplicate behind in edit mode.
            temp = bpy.data.objects.get("dreamuv_temp")
            if temp:
                if bpy.context.mode != "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")
                mesh = temp.data
                bpy.data.objects.remove(temp)
                if mesh.users == 0:
                    bpy.data.meshes.remove(mesh)
    return {"result": list(ret), "object": obj.name, "materials": [m.name for m in obj.data.materials]}
