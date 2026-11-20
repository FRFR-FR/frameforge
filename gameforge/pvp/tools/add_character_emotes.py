#!/usr/bin/env python3
"""Add three named, rig-driven emotes to every existing Loomglass character and re-export GLBs."""
from __future__ import annotations
import argparse
import json
import math
import struct
import sys
from pathlib import Path
import bpy
from mathutils import Euler

EXPECTED = ("Aster", "Bront", "Koro", "Luma", "Miri", "Nyx", "Orin", "Pika", "Sola", "Vey")
EMOTES = ("Emote_Wave", "Emote_Guard", "Emote_Victory")

def arguments():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--audit", required=True)
    return parser.parse_args(argv)

def set_pose(rig, frame, values):
    for bone_name, rotation in values.items():
        bone = rig.pose.bones.get(bone_name)
        if bone is None:
            raise RuntimeError(f"Required humanoid bone missing: {bone_name}")
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = Euler(rotation, "XYZ")
        bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=bone_name)

def make_action(rig, character, action_name, poses):
    action = bpy.data.actions.new(f"{character}_{action_name}")
    rig.animation_data_create()
    rig.animation_data.action = action
    for frame, values in poses:
        set_pose(rig, frame, values)
    return action

def glb_json(path: Path):
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise RuntimeError(f"Invalid GLB header: {path}")
    json_size = struct.unpack("<I", data[12:16])[0]
    return json.loads(data[20:20 + json_size].decode("utf-8"))

def main():
    args = arguments()
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    found = {}
    for rig in arms:
        ident = str(rig.get("character_id", ""))
        name = ident.split("_", 1)[-1].title() if "_" in ident else rig.name.replace("_Rig", "")
        if name in EXPECTED:
            found[name] = rig
    missing = sorted(set(EXPECTED) - set(found))
    if missing:
        raise RuntimeError(f"Character blend is missing armatures: {missing}")

    audit = {"characters": [], "failures": []}
    wave = [
        (1, {"spine": (0.0, 0.0, 0.0), "upper_arm.R": (0.15, -0.15, -0.75), "forearm.R": (0.0, 0.0, -0.9), "hand.R": (0.0, 0.0, 0.0)}),
        (12, {"spine": (0.0, -0.08, 0.0), "upper_arm.R": (0.1, -0.15, -1.45), "forearm.R": (0.0, 0.0, -1.05), "hand.R": (0.0, 0.0, 0.45)}),
        (24, {"spine": (0.0, 0.0, 0.0), "upper_arm.R": (0.15, -0.15, -0.75), "forearm.R": (0.0, 0.0, -0.9), "hand.R": (0.0, 0.0, 0.0)}),
    ]
    guard = [
        (1, {"spine": (0.12, 0.0, 0.0), "upper_arm.L": (0.0, 0.0, 0.95), "forearm.L": (0.0, 0.0, -0.85), "upper_arm.R": (0.0, 0.0, -0.95), "forearm.R": (0.0, 0.0, 0.85)}),
        (12, {"spine": (0.12, 0.0, 0.0), "upper_arm.L": (0.0, 0.0, 1.05), "forearm.L": (0.0, 0.0, -0.95), "upper_arm.R": (0.0, 0.0, -1.05), "forearm.R": (0.0, 0.0, 0.95)}),
        (24, {"spine": (0.0, 0.0, 0.0), "upper_arm.L": (0.0, 0.0, 0.0), "forearm.L": (0.0, 0.0, 0.0), "upper_arm.R": (0.0, 0.0, 0.0), "forearm.R": (0.0, 0.0, 0.0)}),
    ]
    victory = [
        (1, {"spine": (0.0, 0.0, 0.0), "upper_arm.L": (0.0, 0.0, 1.7), "forearm.L": (0.0, 0.0, -0.25), "upper_arm.R": (0.0, 0.0, -1.7), "forearm.R": (0.0, 0.0, 0.25), "head": (0.0, 0.0, 0.0)}),
        (18, {"spine": (-0.08, 0.0, 0.0), "upper_arm.L": (0.0, 0.0, 1.9), "forearm.L": (0.0, 0.0, -0.4), "upper_arm.R": (0.0, 0.0, -1.9), "forearm.R": (0.0, 0.0, 0.4), "head": (0.0, 0.0, 0.08)}),
        (36, {"spine": (0.0, 0.0, 0.0), "upper_arm.L": (0.0, 0.0, 1.7), "forearm.L": (0.0, 0.0, -0.25), "upper_arm.R": (0.0, 0.0, -1.7), "forearm.R": (0.0, 0.0, 0.25), "head": (0.0, 0.0, 0.0)}),
    ]

    for name in EXPECTED:
        rig = found[name]
        meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == rig]
        mesh = meshes[0] if meshes else None
        if mesh is None:
            raise RuntimeError(f"{name}: unified skinned mesh not found")
        bone_names = {b.name for b in rig.data.bones}
        required = {"root", "pelvis", "spine", "neck", "head", "upper_arm.L", "forearm.L", "hand.L",
                    "upper_arm.R", "forearm.R", "hand.R", "thigh.L", "shin.L", "foot.L",
                    "thigh.R", "shin.R", "foot.R"}
        if not required.issubset(bone_names):
            raise RuntimeError(f"{name}: incomplete humanoid skeleton; missing {sorted(required - bone_names)}")
        for act in list(bpy.data.actions):
            if act.name.startswith(name + "_Emote_"):
                bpy.data.actions.remove(act)
        make_action(rig, name, "Emote_Wave", wave)
        make_action(rig, name, "Emote_Guard", guard)
        make_action(rig, name, "Emote_Victory", victory)
        idle = next((a for a in bpy.data.actions if name.lower() in a.name.lower() and "idle" in a.name.lower()), None)
        if idle is None:
            raise RuntimeError(f"{name}: original idle animation missing")
        rig.animation_data.action = idle

        old_location = rig.location.copy()
        rig.location = (0.0, 0.0, 0.0)
        bpy.ops.object.select_all(action="DESELECT")
        rig.select_set(True)
        for mesh_obj in meshes:
            mesh_obj.select_set(True)
        bpy.context.view_layer.objects.active = rig
        target = out / f"{name}.glb"
        bpy.ops.export_scene.gltf(
            filepath=str(target), export_format="GLB", use_selection=True,
            export_animations=True, export_skins=True, export_materials="EXPORT",
            export_animation_mode="ACTIONS", export_force_sampling=True,
            export_cameras=False, export_lights=False
        )
        rig.location = old_location
        bpy.ops.object.select_all(action="DESELECT")
        payload = glb_json(target)
        animation_names = [a.get("name", "") for a in payload.get("animations", [])]
        skin_joints = max((len(s.get("joints", [])) for s in payload.get("skins", [])), default=0)
        required_anims = ("Emote_Wave", "Emote_Guard", "Emote_Victory")
        checks = {
            "glb_exists": target.is_file() and target.stat().st_size > 50000,
            "skinned_armature": bool(payload.get("skins")) and skin_joints >= 17,
            "idle_animation": any("idle" in n.lower() for n in animation_names),
            "three_emotes": all(any(key.lower() in n.lower() for n in animation_names) for key in required_anims),
            "mesh_present": any("mesh" in n for n in payload.get("nodes", [])),
        }
        if not all(checks.values()):
            audit["failures"].append({"character": name, "checks": checks, "animations": animation_names, "skin_joints": skin_joints})
        audit["characters"].append({
            "name": name, "file": target.name, "bytes": target.stat().st_size,
            "bone_count": len(bone_names), "skin_joints": skin_joints,
            "animations": animation_names, "checks": checks
        })
        if not all(checks.values()):
            raise RuntimeError(f"{name}: exported GLB failed rig/animation audit: {checks}")

    if len(audit["characters"]) != 10 or audit["failures"]:
        raise RuntimeError(f"Character export audit failed: {audit['failures']}")
    Path(args.audit).write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print("Verified 10 skinned Loomglass characters, 17+ bones each, Idle plus three emotes each.")

if __name__ == "__main__":
    main()
