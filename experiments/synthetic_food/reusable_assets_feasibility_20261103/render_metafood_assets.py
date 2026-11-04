"""CPU-only Blender appearance feasibility render for five MetaFood3D proxies.

This script intentionally rescales each scanned object for framing. The renders
are appearance previews only: source scale and mass labels are not preserved.
"""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


ASSETS = {
    "steamed-rice": ("Rice", "new_rice_2/rice_2.obj", "Rice"),
    "chicken-dum-biryani": ("Fried_rice", "new_fried_rice_1/fried_rice_1.obj", "Biryani proxy"),
    "Bottle-gourd-curry": ("Stew_Beef", "new_beef_stew_2/beef_stew_2.obj", "Curry proxy"),
    "phulka": ("Tortilla", "new_tortilla_1/tortilla_1.obj", "Flatbread proxy"),
    "salad": ("Coleslaw", "new_coleslaw_2/coleslaw_2.obj", "Salad proxy"),
}


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.materials, bpy.data.meshes, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def look_at(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


def setup_render(path):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 420
    scene.render.resolution_y = 340
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.22, 0.22, 0.22)
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    scene.render.filepath = str(path)

    bpy.ops.object.camera_add(location=(2.4, -3.4, 4.3))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.65
    look_at(camera, (0, 0, 0.35))
    scene.camera = camera

    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.025))
    ground = bpy.context.object
    ground.name = "PreviewGround"
    mat = bpy.data.materials.new("PreviewGroundMat")
    mat.diffuse_color = (0.72, 0.69, 0.61, 1)
    mat.use_nodes = True
    mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (0.72, 0.69, 0.61, 1)
    mat.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = 0.8
    ground.data.materials.append(mat)

    bpy.ops.object.light_add(type="AREA", location=(0.5, -1.3, 4.0))
    key = bpy.context.object
    key.data.energy = 520
    key.data.shape = "DISK"
    key.data.size = 3.5
    look_at(key, (0, 0, 0))
    bpy.ops.object.light_add(type="AREA", location=(-2.0, 1.5, 2.5))
    fill = bpy.context.object
    fill.data.energy = 180
    fill.data.size = 3.0
    look_at(fill, (0, 0, 0.3))


def import_obj(path):
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis="Y", up_axis="Z")
    return [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]


def normalize_for_preview(objects):
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    size = high - low
    factor = 1.55 / max(size.x, size.y, size.z)
    center = (low + high) * 0.5
    for obj in objects:
        obj.location = (obj.location - center) * factor
        obj.scale = obj.scale * factor
        obj.location.z += -low.z * factor + 0.02
    bpy.context.view_layer.update()
    return {"original_bounds": {"min": list(low), "max": list(high)}, "visual_rescale_factor": factor}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh-root", required=True)
    parser.add_argument("--output", required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    mesh_root = Path(args.mesh_root).resolve()
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for wed_class, (category, rel_obj, proxy) in ASSETS.items():
        reset_scene()
        obj_path = mesh_root / category / rel_obj
        setup_render(out / f"{wed_class}.png")
        objects = import_obj(obj_path)
        if not objects:
            raise RuntimeError(f"No mesh imported from {obj_path}")
        bounds = normalize_for_preview(objects)
        bpy.context.scene.render.filepath = str(out / f"{wed_class}.png")
        bpy.ops.render.render(write_still=True)
        rows.append({
            "wed_class": wed_class,
            "asset_category": category,
            "proxy_label": proxy,
            "source_obj": obj_path.relative_to(mesh_root).as_posix(),
            "source_obj_bytes": obj_path.stat().st_size,
            "mesh_object_count": len(objects),
            **bounds,
            "purpose": "appearance-only preview; rescaled; labels invalid for WED supervision",
        })
    (out / "assets.json").write_text(json.dumps({
        "engine": "Blender Cycles CPU",
        "resolution": [420, 340],
        "purpose": "five-class scanned-mesh appearance feasibility",
        "license": "MetaFood3D CC BY-NC 4.0; noncommercial research only",
        "ground_truth_status": "NOT_VALID: source mesh metric scale, exact WED identity, food-only mask, density and mass are not established",
        "items": rows,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
