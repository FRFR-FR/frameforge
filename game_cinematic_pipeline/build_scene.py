#!/usr/bin/env python3
"""FrameForge procedural game-cinematic builder for Blender background mode."""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector


def arguments():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("audit", "render"), default="audit")
    parser.add_argument("--spec", default="game_cinematic_pipeline/scene_spec.json")
    parser.add_argument("--output-dir", default="output/game_cinematic")
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    return parser.parse_args(argv)


def rgba(value, fallback):
    return tuple(value) if isinstance(value, list) and len(value) == 4 else fallback


def make_material(name, color, metallic=0.0, roughness=0.5, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if emission > 0:
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = color
                bsdf.inputs["Emission Strength"].default_value = emission
            elif "Emission" in bsdf.inputs:
                bsdf.inputs["Emission"].default_value = color
                bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def add_box(name, location, scale, material, bevel=0.08, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    if bevel > 0:
        mod = obj.modifiers.new("Machined edge highlights", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    if parent:
        obj.parent = parent
    return obj


def add_area(name, location, target, energy, color, size):
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.color = color
    light.data.shape = "DISK"
    light.data.size = size
    light.rotation_euler = (Vector(target) - light.location).to_track_quat("-Z", "Y").to_euler()
    return light


def animate_rotation(obj, axis, values, frames):
    for frame, angle in zip(frames, values):
        obj.rotation_euler[axis] = angle
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)


def build(spec):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights, bpy.data.materials):
        pass

    project = spec.get("project", {})
    render_cfg = spec.get("render", {})
    env = spec.get("environment", {})
    hero_cfg = spec.get("hero", {})
    duration = max(2, int(render_cfg.get("duration_seconds", 8)))
    fps = max(12, int(render_cfg.get("fps", 24)))
    width = max(320, int(render_cfg.get("width", 1280)))
    height = max(180, int(render_cfg.get("height", 720)))
    frames = duration * fps

    ground_col = rgba(env.get("ground_color"), (0.025, 0.045, 0.065, 1))
    sky_col = rgba(env.get("sky_color"), (0.012, 0.022, 0.045, 1))
    tower_col = rgba(env.get("tower_color"), (0.055, 0.085, 0.12, 1))
    accent_col = rgba(env.get("accent_color"), (0.02, 0.55, 0.72, 1))
    warm_col = rgba(env.get("warm_light_color"), (1.0, 0.32, 0.09, 1))
    armor_col = rgba(hero_cfg.get("armor_color"), (0.12, 0.19, 0.25, 1))
    hero_accent = rgba(hero_cfg.get("accent_color"), accent_col)

    ground = make_material("Wet basalt | PBR", ground_col, 0.28, 0.32)
    tower = make_material("Graphite alloy", tower_col, 0.62, 0.34)
    armor = make_material("Scout armor", armor_col, 0.72, 0.27)
    trim = make_material("Ion cyan emissive", hero_accent, 0.35, 0.24, 2.2)
    cyan = make_material("Outpost signage", accent_col, 0.15, 0.3, 3.0)
    amber = make_material("Warning lamps", warm_col, 0.1, 0.3, 2.4)
    glass = make_material("Dark visor", (0.008, 0.025, 0.04, 1), 0.8, 0.12)

    world = bpy.data.worlds.new("Outpost dusk atmosphere") if not bpy.data.worlds else bpy.data.worlds[0]
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = sky_col
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.22

    add_box("Ground platform", (0, 0, -0.35), (48, 34, 0.7), ground, 0.15)
    # Walkway panels and emissive guide strips.
    for x in range(-18, 20, 4):
        add_box("Walkway seam", (x, -1.2, 0.012), (0.035, 5.0, 0.025), cyan, 0.005)
    for y in (-3.5, 1.0):
        add_box("Raised walkway rail", (0, y, 0.16), (42, 0.18, 0.3), tower, 0.04)

    # Repeating industrial towers create a layered game-world skyline.
    for i, x in enumerate((-17, -12, -7, 8, 13, 18)):
        height_t = 5.0 + (i % 3) * 2.0
        add_box("Outpost tower %02d" % i, (x, 7.0, height_t / 2), (3.0, 3.2, height_t), tower, 0.12)
        add_box("Tower cyan light %02d" % i, (x, 5.35, height_t * 0.64), (1.5, 0.035, 0.16), cyan, 0.01)
        add_box("Tower amber beacon %02d" % i, (x, 7.0, height_t + 0.22), (0.28, 0.28, 0.18), amber, 0.03)
        for level in range(2, int(height_t), 2):
            add_box("Tower window", (x, 5.36, level), (0.85, 0.04, 0.42), glass, 0.015)

    # Cargo containers and pipes provide readable foreground silhouettes.
    for i, x in enumerate((-8, -5, 5, 8)):
        crate = add_box("Cargo module %02d" % i, (x, -2.3, 0.85), (2.0, 1.5, 1.7), tower, 0.12)
        for z in (0.3, 1.35):
            add_box("Cargo cyan latch", (x, -3.08, z), (0.55, 0.035, 0.09), cyan, 0.01)
    for x in (-15, 15):
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.12, depth=18, location=(x, 2.8, 1.8), rotation=(0, math.radians(90), 0))
        pipe = bpy.context.object
        pipe.name = "Industrial conduit"
        pipe.data.materials.append(tower)

    # Procedural armored scout, built entirely from editable 3D primitives.
    root = bpy.data.objects.new("HERO | " + str(hero_cfg.get("name", "Outpost Scout")), None)
    bpy.context.collection.objects.link(root)
    root.location = (float(hero_cfg.get("start_x", -2.2)), -0.2, 0)
    parts = []
    parts.append(add_box("Scout torso", (0, 0, 2.05), (0.95, 0.55, 1.2), armor, 0.16, root))
    parts.append(add_box("Scout chest plate", (0, -0.31, 2.18), (0.58, 0.08, 0.62), trim, 0.07, root))
    parts.append(add_box("Scout backpack", (0, 0.38, 2.12), (0.72, 0.34, 0.9), tower, 0.12, root))
    parts.append(add_box("Scout helmet", (0, 0, 2.92), (0.72, 0.62, 0.68), armor, 0.18, root))
    parts.append(add_box("Scout visor", (0, -0.325, 2.94), (0.52, 0.035, 0.22), glass, 0.025, root))
    parts.append(add_box("Scout left shoulder", (-0.62, 0, 2.42), (0.38, 0.5, 0.42), armor, 0.1, root))
    parts.append(add_box("Scout right shoulder", (0.62, 0, 2.42), (0.38, 0.5, 0.42), armor, 0.1, root))
    left_arm = add_box("Scout left arm", (-0.68, 0, 1.92), (0.28, 0.34, 0.82), armor, 0.09, root)
    right_arm = add_box("Scout right arm", (0.68, 0, 1.92), (0.28, 0.34, 0.82), armor, 0.09, root)
    parts.extend((left_arm, right_arm))
    left_leg = add_box("Scout left leg", (-0.25, 0, 0.82), (0.34, 0.42, 0.92), armor, 0.09, root)
    right_leg = add_box("Scout right leg", (0.25, 0, 0.82), (0.34, 0.42, 0.92), armor, 0.09, root)
    parts.extend((left_leg, right_leg))
    parts.append(add_box("Scout left boot", (-0.25, -0.12, 0.22), (0.42, 0.66, 0.28), tower, 0.07, root))
    parts.append(add_box("Scout right boot", (0.25, -0.12, 0.22), (0.42, 0.66, 0.28), tower, 0.07, root))

    start_x = float(hero_cfg.get("start_x", -2.2))
    end_x = float(hero_cfg.get("end_x", 1.2))
    root.location.x = start_x
    root.keyframe_insert(data_path="location", frame=1)
    root.location.x = end_x
    root.keyframe_insert(data_path="location", frame=frames)
    for obj, axis, sign in ((left_arm, 0, 1), (right_arm, 0, -1), (left_leg, 0, -1), (right_leg, 0, 1)):
        animate_rotation(obj, axis, (0.28 * sign, -0.28 * sign, 0.28 * sign), (1, max(2, frames // 2), frames))
    for obj in parts:
        if obj.animation_data and obj.animation_data.action:
            for fc in obj.animation_data.action.fcurves:
                for key in fc.keyframe_points:
                    key.interpolation = "BEZIER"

    # A foreground drone gives the shot an additional depth layer.
    drone = add_box("Patrol drone body", (4.5, -1.5, 3.6), (1.15, 0.48, 0.28), tower, 0.1)
    drone_light = add_box("Patrol drone light", (4.5, -1.76, 3.6), (0.48, 0.04, 0.08), amber, 0.02)
    for obj in (drone, drone_light):
        obj.keyframe_insert(data_path="location", frame=1)
        obj.location.x -= 3.0
        obj.keyframe_insert(data_path="location", frame=frames)

    # Cinematic key/fill/rim lighting.
    add_area("Cool key light", (1, -8, 10), (0, 0, 1.5), 1800, (0.46, 0.72, 1.0), 8)
    add_area("Warm rim light", (-8, 3, 7), (0, 0, 2), 2200, (1.0, 0.28, 0.09), 6)
    add_area("Overhead softbox", (0, 4, 12), (0, 0, 0), 1500, (0.22, 0.48, 0.8), 7)

    # Camera tracks the hero while moving into the outpost.
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 1.8))
    target = bpy.context.object
    target.name = "Camera tracking target"
    target.keyframe_insert(data_path="location", frame=1)
    target.location.x = end_x
    target.keyframe_insert(data_path="location", frame=frames)
    bpy.ops.object.camera_add(location=(8.5, -13.5, 6.2))
    camera = bpy.context.object
    camera.name = "Game cinematic | tracking camera"
    camera.data.lens = 42
    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    camera.location = (8.5, -13.5, 6.2)
    camera.keyframe_insert(data_path="location", frame=1)
    camera.location = (4.8, -10.5, 5.0)
    camera.keyframe_insert(data_path="location", frame=frames)
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = frames
    scene.render.fps = fps
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = max(8, int(render_cfg.get("samples", 32)))
    scene.cycles.use_denoising = bool(render_cfg.get("denoising", True))
    scene.view_settings.view_transform = "AgX"
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.camera.data.dof.use_dof = True
    scene.camera.data.dof.focus_object = root
    scene.camera.data.dof.aperture_fstop = 5.6
    scene.render.filepath = "//"
    scene.frame_set(1)
    scene["frameforge_project"] = project.get("name", "FrameForge Game Cinematic")
    scene["frameforge_image_generation"] = False
    scene["frameforge_native_3d"] = True
    return scene, frames


def main():
    args = arguments()
    if args.shard_count < 1 or not (0 <= args.shard_index < args.shard_count):
        raise SystemExit("Invalid shard index/count")
    os.makedirs(args.output_dir, exist_ok=True)
    with open(args.spec, "r", encoding="utf-8") as handle:
        spec = json.load(handle)
    scene, total_frames = build(spec)
    project_path = os.path.join(args.output_dir, "FrameForge_Game_Cinematic.blend")
    report_path = os.path.join(args.output_dir, "FrameForge_Game_Cinematic_Audit.json")

    report = {
        "project": spec.get("project", {}).get("name", "FrameForge Game Cinematic"),
        "native_3d_geometry": True,
        "image_generation": False,
        "render_engine": scene.render.engine,
        "device": scene.cycles.device,
        "frame_count": total_frames,
        "objects": len(scene.objects),
        "camera": scene.camera.name if scene.camera else None,
        "status": "passed" if scene.camera and len(scene.objects) >= 30 else "failed"
    }
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    if report["status"] != "passed":
        raise RuntimeError("Scene audit failed: camera or required scene geometry missing")

    bpy.ops.wm.save_as_mainfile(filepath=project_path)
    # glTF export is a useful interchange deliverable; keep the .blend authoritative.
    try:
        bpy.ops.export_scene.gltf(filepath=os.path.join(args.output_dir, "FrameForge_Game_Cinematic.glb"), export_format="GLB")
    except Exception as exc:
        print("GLB export unavailable; .blend remains authoritative:", exc)

    if args.mode == "render":
        start = (total_frames * args.shard_index) // args.shard_count + 1
        end = (total_frames * (args.shard_index + 1)) // args.shard_count
        if end < start:
            raise RuntimeError("Empty render shard")
        frames_dir = os.path.join(args.output_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)
        scene.frame_start = start
        scene.frame_end = end
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = os.path.join(frames_dir, "frame_")
        bpy.ops.render.render(animation=True)
        print("Rendered frames %d-%d of %d" % (start, end, total_frames))


if __name__ == "__main__":
    main()
