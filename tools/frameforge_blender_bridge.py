#!/usr/bin/env python3
"""FrameForge V2 Blender bridge.

Reads the portable FrameForge 3D scene manifest, creates/updates a Blender scene,
applies basic object animation and explicit ground/AABB contact approximations,
and can render a PNG frame for re-import into FrameForge.

Run:
  blender --background --python tools/frameforge_blender_bridge.py -- \
    --project frameforge_blender_scene.json --output-dir output/frameforge --mode build
  blender --background --python tools/frameforge_blender_bridge.py -- \
    --project frameforge_blender_scene.json --output-dir output/frameforge --mode render
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path


def read_manifest(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("format") != "frameforge-blender-scene" or data.get("schema_version") != 1:
        raise ValueError("Unsupported FrameForge Blender bridge manifest.")
    settings = data.get("settings") or {}
    width = int(settings.get("width", 1280))
    height = int(settings.get("height", 720))
    fps = float(settings.get("fps", 30))
    if not (1 <= width <= 16384 and 1 <= height <= 16384 and 0 < fps <= 240):
        raise ValueError("Invalid output dimensions or frame rate.")
    for model in data.get("models", []):
        rel = model.get("asset_path", "")
        if not rel or os.path.isabs(rel):
            raise ValueError("Every model needs a relative asset_path.")
        target = (Path(path).resolve().parent / rel).resolve()
        root = Path(path).resolve().parent
        if root not in target.parents or not target.is_file():
            raise FileNotFoundError("Missing or unsafe model path: " + rel)
    return data


def args_from_cli(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--output-dir", default="output/frameforge_blender")
    parser.add_argument("--mode", choices=("build", "render"), default="build")
    parser.add_argument("--frame", type=int, default=1, help="Frame to render in render mode.")
    return parser.parse_args(argv)


def xyz(value, default=(0.0, 0.0, 0.0)):
    values = list(value or default)
    if len(values) != 3:
        raise ValueError("3D vectors must have exactly three coordinates.")
    return tuple(float(v) for v in values)


def hex_rgba(value, default=(0.5, 0.5, 0.5, 1.0)):
    if not isinstance(value, str) or not value.startswith("#"):
        return default
    raw = value[1:]
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) != 6:
        return default
    return tuple(int(raw[index:index + 2], 16) / 255.0 for index in (0, 2, 4)) + (1.0,)


def clear_scene(bpy):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights, bpy.data.materials, bpy.data.actions):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def create_material(bpy, name, config):
    material = bpy.data.materials.new(name=name)
    material.diffuse_color = hex_rgba(config.get("color", "#8ea8c8"))
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled:
        principled.inputs["Base Color"].default_value = material.diffuse_color
        principled.inputs["Metallic"].default_value = float(config.get("metallic", 0.0))
        principled.inputs["Roughness"].default_value = float(config.get("roughness", 0.72))
    return material


def add_primitive(bpy, item):
    kind = item.get("primitive", "cube")
    location = xyz(item.get("position"))
    dimensions = xyz(item.get("dimensions"), (1.0, 1.0, 1.0))
    if kind == "cube":
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
        obj = bpy.context.object
        obj.dimensions = dimensions
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    elif kind == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.5, location=location)
        obj = bpy.context.object
        obj.dimensions = dimensions
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    elif kind == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.5, depth=1.0, location=location)
        obj = bpy.context.object
        obj.dimensions = dimensions
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    elif kind == "plane":
        bpy.ops.mesh.primitive_plane_add(size=max(dimensions[0], dimensions[1]), location=location)
        obj = bpy.context.object
        obj.dimensions = dimensions
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    else:
        raise ValueError("Unsupported bridge primitive: " + str(kind))
    obj.name = item.get("name") or item.get("id") or kind.title()
    obj["frameforge_id"] = str(item.get("id", obj.name))
    if item.get("material"):
        obj.data.materials.append(create_material(bpy, obj.name + " Material", item["material"]))
    return obj


def import_model(bpy, manifest_path, model):
    root = Path(manifest_path).resolve().parent
    filepath = (root / model["asset_path"]).resolve()
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(filepath))
    created = [obj for obj in bpy.context.scene.objects if obj not in before]
    if not created:
        raise RuntimeError("glTF importer returned no objects for " + model["asset_path"])
    root_obj = next((obj for obj in created if obj.parent is None), created[0])
    root_obj.name = model.get("name") or model.get("asset_id") or filepath.stem
    root_obj["frameforge_id"] = str(model.get("asset_id", root_obj.name))
    transform = model.get("transform") or {}
    root_obj.location = xyz(transform.get("position"))
    root_obj.rotation_euler = xyz(transform.get("rotation"))
    root_obj.scale = xyz(transform.get("scale"), (1.0, 1.0, 1.0))
    animation_name = (model.get("animation") or {}).get("clip_name", "")
    time_scale = max(0.001, float((model.get("animation") or {}).get("time_scale", 1.0)))
    if animation_name and (model.get("animation") or {}).get("enabled", True):
        action = bpy.data.actions.get(animation_name)
        if action:
            for obj in created:
                if obj.type == "ARMATURE":
                    obj.animation_data_create()
                    track = obj.animation_data.nla_tracks.new()
                    strip = track.strips.new(action.name, int(model.get("start_frame", 0)) + 1, action)
                    strip.scale = 1.0 / time_scale
                    if (model.get("animation") or {}).get("loop", True) is False:
                        strip.repeat = 1.0
    # V2 3D transform keys are clip-local and component-based.
    clip_start = int(model.get("start_frame", 0)) + 1
    field_map = {
        "position3d": ("location", False),
        "rotation3d": ("rotation_euler", True),
        "scale3d": ("scale", False)
    }
    interpolation_map = {
        "linear": "LINEAR", "step": "CONSTANT",
        "ease_in": "BEZIER", "ease_out": "BEZIER",
        "ease_in_out": "BEZIER", "bezier": "BEZIER"
    }
    for key in model.get("keyframes", []):
        property_name = str(key.get("property", ""))
        parts = property_name.split(".")
        if len(parts) != 2 or parts[0] not in field_map or parts[1] not in ("x", "y", "z"):
            continue
        data_path, radians = field_map[parts[0]]
        index = ("x", "y", "z").index(parts[1])
        value = float(key.get("value", 0.0))
        if radians:
            value = math.radians(value)
        frame = clip_start + int(key.get("frame", 0))
        root_obj.path_resolve(data_path)[index] = value
        root_obj.keyframe_insert(data_path=data_path, index=index, frame=frame)
        action_data = root_obj.animation_data.action if root_obj.animation_data else None
        if action_data:
            for curve in action_data.fcurves:
                if curve.data_path == data_path and curve.array_index == index:
                    for point in curve.keyframe_points:
                        if abs(point.co.x - frame) < 0.01:
                            point.interpolation = interpolation_map.get(key.get("interpolation", "ease_in_out"), "BEZIER")
    return root_obj, created


def setup_camera(bpy, config):
    data = bpy.data.cameras.new("FrameForge V2 Camera")
    camera = bpy.data.objects.new("FrameForge V2 Camera", data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = xyz(config.get("position"), (6.0, 4.0, 7.0))
    target = xyz(config.get("target"))
    direction = tuple(target[index] - camera.location[index] for index in range(3))
    from mathutils import Vector
    camera.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    if config.get("projection") == "orthographic":
        data.type = "ORTHO"
        data.ortho_scale = float(config.get("orthographic_height", 8.0))
    else:
        data.type = "PERSP"
        data.lens = max(10.0, min(120.0, float(config.get("fov", 45.0)))) * 1.2
    bpy.context.scene.camera = camera
    return camera


def setup_lights(bpy, lights):
    for index, config in enumerate(lights or []):
        kind = config.get("type", "directional")
        light_type = "AREA" if kind == "ambient" else ("POINT" if kind == "point" else ("SPOT" if kind == "spot" else "AREA"))
        data = bpy.data.lights.new("FrameForge " + kind.title() + " " + str(index + 1), type=light_type)
        obj = bpy.data.objects.new(data.name, data)
        bpy.context.scene.collection.objects.link(obj)
        data.color = hex_rgba(config.get("color", "#ffffff"))[:3]
        data.energy = max(0.0, float(config.get("intensity", 1.0))) * (120.0 if kind == "ambient" else 900.0)
        obj.location = xyz(config.get("position"), (0.0, 3.0, 2.0))
        if kind == "directional":
            direction = xyz(config.get("direction"), (-0.55, 0.78, 0.48))
            from mathutils import Vector
            obj.rotation_euler = Vector(tuple(-v for v in direction)).to_track_quat("-Z", "Y").to_euler()
        if kind == "spot":
            data.spot_size = float(config.get("angle", math.pi / 4))
            data.spot_blend = float(config.get("penumbra", 0.2))
    return


def animate_object(obj, keyframes):
    for key in keyframes or []:
        frame = int(key.get("frame", 1))
        if "position" in key:
            obj.location = xyz(key["position"])
            obj.keyframe_insert(data_path="location", frame=frame)
        if "rotation" in key:
            rotation = xyz(key["rotation"])
            obj.rotation_euler = tuple(math.radians(v) for v in rotation)
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)
        if "scale" in key:
            obj.scale = xyz(key["scale"], (1.0, 1.0, 1.0))
            obj.keyframe_insert(data_path="scale", frame=frame)


def world_bounds(obj):
    from mathutils import Vector
    candidates = [obj] + list(getattr(obj, "children_recursive", []))
    points = []
    for candidate in candidates:
        if candidate.type != "MESH":
            continue
        points.extend(candidate.matrix_world @ Vector(corner) for corner in candidate.bound_box)
    if not points:
        points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    if not points:
        origin = obj.matrix_world.translation
        points = [origin]
    return (
        min(point.x for point in points), min(point.y for point in points), min(point.z for point in points),
        max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)
    )


def solve_contacts(bpy, objects, constraints_by_id, frame):
    """Apply explicit ground clamping and simple vertical AABB separation; not a physics solver."""
    scene = bpy.context.scene
    scene.frame_set(frame)
    id_objects = {str(obj.get("frameforge_id", obj.name)): obj for obj in objects}
    for obj in objects:
        config = constraints_by_id.get(str(obj.get("frameforge_id", obj.name)), [])
        for constraint in config:
            if constraint.get("enabled", True) is False or constraint.get("type") != "ground_contact":
                continue
            ground_z = float(constraint.get("ground_y", 0.0))
            offset = float(constraint.get("offset", 0.0))
            bpy.context.view_layer.update()
            bounds = world_bounds(obj)
            obj.location.z += ground_z + offset - bounds[2]
    colliders = []
    for obj in objects:
        if any(item.get("type") == "aabb_collision" and item.get("enabled", True) is not False for item in constraints_by_id.get(str(obj.get("frameforge_id", obj.name)), [])):
            colliders.append(obj)
    for index, left in enumerate(colliders):
        for right in colliders[index + 1:]:
            bpy.context.view_layer.update()
            a, b = world_bounds(left), world_bounds(right)
            intersects = a[0] < b[3] and a[3] > b[0] and a[1] < b[4] and a[4] > b[1] and a[2] < b[5] and a[5] > b[2]
            if intersects:
                right.location.x += max(0.0, a[3] - b[0]) + 0.001
                right["frameforge_contact"] = "AABB horizontal separation approximation"
    bpy.context.view_layer.update()


def build_scene(bpy, manifest, manifest_path, output_dir):
    clear_scene(bpy)
    scene = bpy.context.scene
    settings = manifest.get("settings", {})
    scene.render.resolution_x = int(settings.get("width", 1280))
    scene.render.resolution_y = int(settings.get("height", 720))
    scene.render.resolution_percentage = int(settings.get("resolution_percentage", 100))
    scene.render.fps = int(round(float(settings.get("fps", 30))))
    scene.frame_start = int(settings.get("start_frame", 1))
    scene.frame_end = int(settings.get("end_frame", max(scene.frame_start, 48)))
    engine = str(settings.get("render_engine", "CYCLES"))
    available_engines = {item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items}
    if engine not in available_engines:
        engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in available_engines else (
            "BLENDER_EEVEE" if "BLENDER_EEVEE" in available_engines else "BLENDER_WORKBENCH"
        )
    scene.render.engine = engine
    if engine == "CYCLES":
        scene.cycles.device = "CPU"
        scene.cycles.samples = max(1, min(256, int(settings.get("samples", 16))))
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = max(1, min(64, int(settings.get("samples", 16))))
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = bool((manifest.get("scene") or {}).get("environment", {}).get("transparent", False))
    scene.render.filepath = os.path.join(output_dir, "frameforge_")
    scene.world.color = (0.02, 0.03, 0.05)
    background = (manifest.get("scene") or {}).get("environment", {}).get("background")
    if background and scene.world and scene.world.use_nodes:
        node = scene.world.node_tree.nodes.get("Background")
        if node:
            node.inputs["Color"].default_value = hex_rgba(background)
    camera_config = (manifest.get("scene") or {}).get("camera", {})
    setup_camera(bpy, camera_config)
    setup_lights(bpy, (manifest.get("scene") or {}).get("lights", []))
    roots, all_objects, constraints_by_id = [], [], {}
    for item in manifest.get("objects", []):
        obj = add_primitive(bpy, item)
        roots.append(obj)
        all_objects.append(obj)
        constraints_by_id[str(item.get("id", obj.name))] = item.get("constraints", [])
        animate_object(obj, item.get("keyframes", []))
    for model in manifest.get("models", []):
        root, imported = import_model(bpy, manifest_path, model)
        roots.append(root)
        all_objects.extend(imported)
        constraints_by_id[str(model.get("asset_id", root.name))] = model.get("constraints", [])
    # Ground surface is optional; the ground-contact constraint can operate without one.
    floor = manifest.get("ground")
    if floor:
        bpy.ops.mesh.primitive_plane_add(size=float(floor.get("size", 30.0)), location=xyz(floor.get("position"), (0, 0, 0)))
        floor_obj = bpy.context.object
        floor_obj.name = floor.get("name", "Ground")
        floor_obj.data.materials.append(create_material(bpy, "Ground Material", floor.get("material", {"color": "#202b38"})))
    scene["frameforge_project_name"] = str(manifest.get("project", {}).get("name", "FrameForge V2 3D Scene"))
    scene["frameforge_manifest_version"] = 1
    scene["frameforge_contact_mode"] = "ground clamp + approximate horizontal AABB separation; not full physics"
    os.makedirs(output_dir, exist_ok=True)
    return scene, roots, all_objects, constraints_by_id


def main(argv=None):
    args = args_from_cli(argv)
    manifest_path = os.path.abspath(args.project)
    manifest = read_manifest(manifest_path)
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    import bpy
    scene, roots, objects, constraints = build_scene(bpy, manifest, manifest_path, output_dir)
    settings = manifest.get("settings", {})
    if args.mode == "build":
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(output_dir, "FrameForge_V2_Scene.blend"))
        try:
            bpy.ops.export_scene.gltf(filepath=os.path.join(output_dir, "FrameForge_V2_Scene.glb"), export_format="GLB")
        except Exception as error:
            print("GLB_EXPORT_WARNING", str(error), flush=True)
        print("FRAMEFORGE_BLENDER_BUILD_PASS", "objects", len(objects), "models", len(manifest.get("models", [])), flush=True)
        return
    frame = max(scene.frame_start, min(scene.frame_end, int(args.frame)))
    solve_contacts(bpy, objects, constraints, frame)
    scene.frame_set(frame)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(output_dir, "FrameForge_V2_Render.png")
    bpy.ops.render.render(write_still=True)
    path = scene.render.filepath
    if not os.path.isfile(path) or os.path.getsize(path) < 512:
        raise RuntimeError("Blender did not produce a valid preview image.")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(output_dir, "FrameForge_V2_Rendered_Scene.blend"))
    print("FRAMEFORGE_BLENDER_RENDER_PASS", path, os.path.getsize(path), "frame", frame, flush=True)


if __name__ == "__main__":
    # Blender appends its own CLI arguments before the -- separator.
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None
    main(argv)
