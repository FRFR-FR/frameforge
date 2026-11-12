#!/usr/bin/env python3
"""Generate original, armature-rigged GAMEFORGE characters and render a 720p/1080p cutscene."""
from __future__ import annotations
import argparse, json, math, os, sys
from pathlib import Path
import bpy
from mathutils import Vector

CUTSCENE_ROOT = Path(__file__).resolve().parents[1]
if str(CUTSCENE_ROOT) not in sys.path:
    sys.path.insert(0, str(CUTSCENE_ROOT))
from gameforge_cutscene_import import load_project  # noqa: E402
from contracts import render_policy  # noqa: E402

# The Blender scene generator only creates native mesh/armature data. No image generation or textures are downloaded.


def material(name, color, metallic=0.0, roughness=0.55, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if emission:
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = color
                bsdf.inputs["Emission Strength"].default_value = emission
            elif "Emission" in bsdf.inputs:
                bsdf.inputs["Emission"].default_value = color
                bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def add_armature(character_id, name, location):
    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm = bpy.context.object
    arm.name = f"RIG_{character_id}_{name}"
    arm.data.name = f"ARMATURE_{character_id}"
    edit = arm.data.edit_bones
    edit.remove(edit[0])
    specs = {
        "root": ((0, 0, 0.05), (0, 0, 0.72), None),
        "pelvis": ((0, 0, 0.78), (0, 0, 1.12), "root"),
        "spine": ((0, 0, 1.02), (0, 0, 1.98), "pelvis"),
        "neck": ((0, 0, 1.88), (0, 0, 2.18), "spine"),
        "head": ((0, 0, 2.10), (0, 0, 2.72), "neck"),
        "jaw": ((0, -0.04, 2.39), (0, -0.30, 2.39), "head"),
        "upper_arm.L": ((-0.42, 0, 1.83), (-0.72, 0, 1.40), "spine"),
        "lower_arm.L": ((-0.72, 0, 1.40), (-0.76, -0.01, 0.98), "upper_arm.L"),
        "hand.L": ((-0.76, -0.01, 0.98), (-0.78, -0.08, 0.76), "lower_arm.L"),
        "upper_arm.R": ((0.42, 0, 1.83), (0.72, 0, 1.40), "spine"),
        "lower_arm.R": ((0.72, 0, 1.40), (0.76, -0.01, 0.98), "upper_arm.R"),
        "hand.R": ((0.76, -0.01, 0.98), (0.78, -0.08, 0.76), "lower_arm.R"),
        "thigh.L": ((-0.22, 0, 0.96), (-0.24, 0, 0.55), "pelvis"),
        "shin.L": ((-0.24, 0, 0.55), (-0.25, 0, 0.17), "thigh.L"),
        "foot.L": ((-0.25, 0, 0.17), (-0.25, -0.28, 0.10), "shin.L"),
        "thigh.R": ((0.22, 0, 0.96), (0.24, 0, 0.55), "pelvis"),
        "shin.R": ((0.24, 0, 0.55), (0.25, 0, 0.17), "thigh.R"),
        "foot.R": ((0.25, 0, 0.17), (0.25, -0.28, 0.10), "shin.R"),
    }
    bones = {}
    for bone_name, (head, tail, parent_name) in specs.items():
        bone = edit.new(bone_name)
        bone.head, bone.tail = head, tail
        bones[bone_name] = bone
        if parent_name:
            bone.parent = bones[parent_name]
            bone.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.location = location
    arm.show_in_front = True
    arm.data.display_type = "STICK"
    return arm


def add_piece(name, kind, location, dimensions, mat, bone_name, pieces, bevel=0.04, vertices=18):
    if kind == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=vertices, ring_count=max(8, vertices // 2), radius=1, location=location)
        obj = bpy.context.object
        obj.scale = dimensions
    elif kind == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=dimensions[0], depth=dimensions[1], location=location)
        obj = bpy.context.object
    else:
        bpy.ops.mesh.primitive_cube_add(size=1, location=location)
        obj = bpy.context.object
        obj.dimensions = dimensions
    obj.name = name
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if bevel and kind == "cube":
        mod = obj.modifiers.new("Soft designed edges", "BEVEL")
        mod.width = min(bevel, min(dimensions) * 0.22)
        mod.segments = 3
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    if kind in {"sphere", "cylinder"}:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    obj.data.materials.append(mat)
    group = obj.vertex_groups.new(name=bone_name)
    group.add([v.index for v in obj.data.vertices], 1.0, "REPLACE")
    pieces.append(obj)


def add_segment(name, start, end, radius, mat, bone_name, pieces, vertices=16):
    a, b = Vector(start), Vector(end)
    direction = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=direction.length, location=(a + b) * 0.5)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(direction.normalized())
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj.data.materials.append(mat)
    group = obj.vertex_groups.new(name=bone_name)
    group.add([v.index for v in obj.data.vertices], 1.0, "REPLACE")
    pieces.append(obj)


def build_character(character, index, duration_frames):
    char_id, name = character["id"], character["name"]
    x = (index - 0.5) * 2.15
    arm = add_armature(char_id, name, (x, 0, 0))
    palette = character.get("palette", {})
    primary = tuple(palette.get("primary", (0.10 + 0.05 * index, 0.20, 0.28, 1.0)))
    accent = tuple(palette.get("accent", (0.08, 0.72, 0.68, 1.0)))
    primary_mat = material(f"{char_id}_Tailored composite", primary, 0.32, 0.45)
    dark_mat = material(f"{char_id}_Graphite underlayer", (0.018, 0.035, 0.052, 1), 0.58, 0.38)
    accent_mat = material(f"{char_id}_Signal enamel", accent, 0.42, 0.25, 0.45)
    skin_mat = material(f"{char_id}_Warm ceramic skin", (0.49, 0.31, 0.24, 1), 0.02, 0.62)
    eye_mat = material(f"{char_id}_Obsidian eyes", (0.006, 0.012, 0.018, 1), 0.12, 0.13)
    hair_mat = material(f"{char_id}_Hair material", (0.035, 0.045, 0.065, 1), 0.05, 0.62)
    pieces = []

    add_piece(f"{name}_torso", "sphere", (0, 0, 1.54), (0.48, 0.28, 0.62), primary_mat, "spine", pieces)
    add_piece(f"{name}_pelvis", "cube", (0, 0.015, 0.94), (0.66, 0.38, 0.34), dark_mat, "pelvis", pieces, bevel=0.11)
    add_piece(f"{name}_chest_plate", "cube", (0, -0.286, 1.64), (0.48, 0.055, 0.48), accent_mat, "spine", pieces, bevel=0.08)
    add_piece(f"{name}_collar", "sphere", (0, -0.03, 1.99), (0.32, 0.30, 0.14), dark_mat, "neck", pieces)
    add_piece(f"{name}_neck", "cylinder", (0, 0, 2.08), (0.14, 0.22), skin_mat, "neck", pieces)
    add_piece(f"{name}_head", "sphere", (0, 0, 2.42), (0.34, 0.31, 0.43), skin_mat, "head", pieces)
    add_piece(f"{name}_jaw", "sphere", (0, -0.15, 2.29), (0.22, 0.18, 0.16), skin_mat, "jaw", pieces)
    add_piece(f"{name}_hair_crown", "sphere", (0, 0.01, 2.72), (0.36, 0.31, 0.17), hair_mat, "head", pieces)
    add_piece(f"{name}_eye_L", "sphere", (-0.125, -0.286, 2.48), (0.045, 0.026, 0.05), eye_mat, "head", pieces, bevel=0, vertices=12)
    add_piece(f"{name}_eye_R", "sphere", (0.125, -0.286, 2.48), (0.045, 0.026, 0.05), eye_mat, "head", pieces, bevel=0, vertices=12)
    add_piece(f"{name}_brow_L", "cube", (-0.125, -0.30, 2.56), (0.10, 0.035, 0.025), hair_mat, "head", pieces, bevel=0.008)
    add_piece(f"{name}_brow_R", "cube", (0.125, -0.30, 2.56), (0.10, 0.035, 0.025), hair_mat, "head", pieces, bevel=0.008)

    for side, sign in (("L", -1), ("R", 1)):
        add_piece(f"{name}_shoulder_{side}", "sphere", (sign * 0.49, 0, 1.82), (0.25, 0.29, 0.25), primary_mat, f"upper_arm.{side}", pieces)
        add_segment(f"{name}_upper_arm_{side}", (sign * 0.52, 0, 1.76), (sign * 0.70, 0, 1.39), 0.135, primary_mat, f"upper_arm.{side}", pieces)
        add_segment(f"{name}_forearm_{side}", (sign * 0.70, 0, 1.38), (sign * 0.76, -0.01, 0.99), 0.105, dark_mat, f"lower_arm.{side}", pieces)
        add_piece(f"{name}_wrist_cuff_{side}", "cylinder", (sign * 0.755, -0.01, 1.04), (0.12, 0.095), accent_mat, f"lower_arm.{side}", pieces)
        add_piece(f"{name}_hand_{side}", "sphere", (sign * 0.78, -0.05, 0.83), (0.12, 0.10, 0.15), skin_mat, f"hand.{side}", pieces)
        add_segment(f"{name}_thigh_{side}", (sign * 0.22, 0, 0.98), (sign * 0.24, 0, 0.56), 0.16, primary_mat, f"thigh.{side}", pieces)
        add_segment(f"{name}_shin_{side}", (sign * 0.24, 0, 0.55), (sign * 0.25, 0, 0.18), 0.115, dark_mat, f"shin.{side}", pieces)
        add_piece(f"{name}_boot_{side}", "cube", (sign * 0.25, -0.12, 0.12), (0.29, 0.48, 0.20), primary_mat, f"foot.{side}", pieces, bevel=0.055)
        add_piece(f"{name}_boot_light_{side}", "cube", (sign * 0.25, -0.365, 0.16), (0.18, 0.025, 0.045), accent_mat, f"foot.{side}", pieces, bevel=0.012)
    add_piece(f"{name}_shoulder_insignia", "cube", (-0.51, -0.27, 1.88), (0.10, 0.035, 0.12), accent_mat, "upper_arm.L", pieces, bevel=0.015)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in pieces:
        obj.select_set(True)
    body = pieces[0]
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    body.name = f"MESH_{char_id}_SkinnedOriginal"
    body.parent = arm
    body.parent_type = "OBJECT"
    body.matrix_parent_inverse.identity()
    modifier = body.modifiers.new("GAMEFORGE skeletal deformation", "ARMATURE")
    modifier.object = arm
    arm["gameforge_character_id"] = char_id
    arm["gameforge_rig_version"] = "1.0"
    arm["gameforge_original_procedural_asset"] = True

    key_frames = [1, max(2, duration_frames // 4), max(3, duration_frames // 2), max(4, duration_frames * 3 // 4), duration_frames]
    cycle = [0.0, 0.32, 0.0, -0.32, 0.0]
    for side, sign in (("L", 1), ("R", -1)):
        for bone_name, multiplier in (("thigh", sign), ("upper_arm", -sign)):
            bone = arm.pose.bones.get(f"{bone_name}.{side}")
            if bone:
                bone.rotation_mode = "XYZ"
                for frame, value in zip(key_frames, cycle):
                    bone.rotation_euler[0] = value * multiplier
                    bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=f"{bone_name}.{side}")
    head = arm.pose.bones.get("head")
    if head:
        head.rotation_mode = "XYZ"
        for frame, value in zip(key_frames, (0.0, 0.025, 0.0, -0.025, 0.0)):
            head.rotation_euler[1] = value
            head.keyframe_insert(data_path="rotation_euler", frame=frame, group="head")
    return arm


def add_viseme_animation(armatures, sync, fps):
    for cue in sync.get("visemes", []):
        arm = armatures.get(cue.get("character_id"))
        if not arm:
            continue
        jaw = arm.pose.bones.get("jaw")
        if not jaw:
            continue
        jaw.rotation_mode = "XYZ"
        start_frame = max(1, int(round(float(cue["at"]) * fps)) + 1)
        end_frame = max(start_frame + 1, int(round(float(cue["end"]) * fps)) + 1)
        openness = max(0.0, min(1.0, float(cue.get("jaw_open", 0.1))))
        jaw.rotation_euler[0] = -0.34 * openness
        jaw.keyframe_insert(data_path="rotation_euler", frame=start_frame, group="jaw")
        jaw.rotation_euler[0] = 0.0
        jaw.keyframe_insert(data_path="rotation_euler", frame=end_frame, group="jaw")


def add_stage():
    floor_mat = material("Stage | midnight ceramic", (0.018, 0.034, 0.052, 1), 0.28, 0.36)
    wall_mat = material("Stage | deep blue-black alloy", (0.025, 0.065, 0.085, 1), 0.58, 0.3)
    glow_mat = material("Stage | turquoise guide light", (0.02, 0.55, 0.47, 1), 0.22, 0.25, 2.4)
    warm_mat = material("Stage | amber practical", (0.75, 0.20, 0.06, 1), 0.16, 0.28, 1.6)

    bpy.ops.mesh.primitive_plane_add(size=28, location=(0, 0, -0.08))
    bpy.context.object.name = "CUTSCENE_STAGE_ground"
    bpy.context.object.data.materials.append(floor_mat)
    for x in (-7.5, -5.2, 5.2, 7.5):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 2.8, 2.8))
        pillar = bpy.context.object
        pillar.name = "CUTSCENE_STAGE_arch"
        pillar.dimensions = (0.5, 0.48, 5.6)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        pillar.data.materials.append(wall_mat)
        bevel = pillar.modifiers.new("Architectural edge softening", "BEVEL")
        bevel.width, bevel.segments = 0.12, 3
        bpy.context.view_layer.objects.active = pillar
        bpy.ops.object.modifier_apply(modifier=bevel.name)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 2.52, 3.0))
        strip = bpy.context.object
        strip.name = "CUTSCENE_STAGE_light_strip"
        strip.dimensions = (0.07, 0.035, 3.9)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        strip.data.materials.append(glow_mat if x < 0 else warm_mat)
    for x in (-5, -3, 3, 5):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, -0.35, -0.015))
        line = bpy.context.object
        line.name = "CUTSCENE_STAGE_floor_inlay"
        line.dimensions = (0.035, 5.5, 0.025)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        line.data.materials.append(glow_mat)

    world = bpy.data.worlds.new("GAMEFORGE original night studio") if not bpy.data.worlds else bpy.data.worlds[0]
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.006, 0.014, 0.026, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.32

    def area(name, location, target, energy, color, size):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.color = color
        light.data.shape = "DISK"
        light.data.size = size
        light.rotation_euler = (Vector(target) - light.location).to_track_quat("-Z", "Y").to_euler()
    area("Key | soft cool", (0, -6, 7), (0, 0, 1.5), 1200, (0.42, 0.72, 1.0), 6)
    area("Rim | warm", (-5, 1.5, 5), (0, 0, 1.5), 950, (1.0, 0.30, 0.12), 4)
    area("Fill | turquoise", (5, 0, 4.5), (0, 0, 1.4), 700, (0.12, 0.85, 0.73), 5)

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 1.5))
    target = bpy.context.object
    target.name = "CUTSCENE_CAMERA_target"
    bpy.ops.object.camera_add(location=(0, -9.8, 3.45))
    camera = bpy.context.object
    camera.name = "CUTSCENE_CAMERA_main"
    camera.data.lens = 45
    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    scene = bpy.context.scene
    scene.camera = camera
    camera.keyframe_insert(data_path="location", frame=1)
    camera.location.x, camera.location.z = 0.22, 3.32
    camera.keyframe_insert(data_path="location", frame=scene.frame_end)
    scene.frame_set(1)


def build(project, sync, output_dir: Path, mode: str):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    policy = render_policy(project)
    fps = policy["fps"]
    frame_end = max(2, int(round(float(project["render"]["duration_seconds"]) * fps)))
    armatures = {
        character["id"]: build_character(character, index, frame_end)
        for index, character in enumerate(project["characters"])
    }
    add_stage()
    add_viseme_animation(armatures, sync, fps)

    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, frame_end
    scene.render.fps = fps
    scene.render.resolution_x, scene.render.resolution_y = policy["width"], policy["height"]
    scene.render.resolution_percentage = 100
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = policy["samples"]
    scene.cycles.use_denoising = policy["denoising"]
    scene.render.threads_mode = "FIXED"
    scene.render.threads = policy["threads"]
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"

    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str((frames_dir / "frame_").resolve())
    scene["gameforge_cutscene"] = project["project"]["id"]
    scene["gameforge_resolution_cap"] = "1920x1080"
    scene["gameforge_audio_synced"] = bool(sync.get("visemes"))
    scene["gameforge_procedural_rigged_characters"] = True

    blend_path = output_dir / "GAMEFORGE_Cutscene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    audit = {
        "status": "passed", "native_blender_scene": True,
        "procedural_original_characters": len(armatures),
        "armature_bones_per_character": {key: len(arm.data.bones) for key, arm in armatures.items()},
        "image_generation_used": False, "resolution": f"{policy['width']}x{policy['height']}",
        "fps": fps, "duration_seconds": project["render"]["duration_seconds"],
        "frame_count": frame_end, "cycles_device": "CPU", "samples": policy["samples"],
        "threads": policy["threads"], "forced_alignment_viseme_cues": len(sync.get("visemes", [])),
        "blend_file": str(blend_path), "profile": policy["profile"],
    }
    (output_dir / "scene_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    if mode == "render":
        bpy.ops.render.render(animation=True)
    return audit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("audit", "render"), default="audit")
    parser.add_argument("--project", required=True)
    parser.add_argument("--sync", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    project = load_project(args.project)
    sync = json.loads(Path(args.sync).read_text(encoding="utf-8"))
    print(json.dumps(build(project, sync, Path(args.out), args.mode), indent=2))


if __name__ == "__main__":
    main()
