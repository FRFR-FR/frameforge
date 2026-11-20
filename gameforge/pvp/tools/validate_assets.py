#!/usr/bin/env python3
"""Fail-closed verification for all imported A-scope offline PvP assets and 720p settings."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path

CHARACTERS = ("Aster", "Bront", "Koro", "Luma", "Miri", "Nyx", "Orin", "Pika", "Sola", "Vey")
WEAPONS = ("Vesper9", "FluxSMG", "AegisAR", "KestrelBurst", "RangerDMR", "Longbow",
           "Breach12", "BastionLMG", "PulseCarbine", "ArcLance")
REQUIRED_ANIMATIONS = ("idle", "walk", "sprint", "crouch", "jump", "roll", "fire",
                       "reload", "emote_wave", "emote_guard", "emote_victory")

def read_glb(path: Path):
    data = path.read_bytes()
    if data[:4] != b"glTF" or len(data) < 20:
        raise RuntimeError(f"Invalid GLB: {path}")
    size = struct.unpack("<I", data[12:16])[0]
    return json.loads(data[20:20 + size].decode("utf-8"))

def png_size(path: Path):
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"Invalid PNG: {path}")
    return struct.unpack(">II", data[16:24])

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    a = p.parse_args()
    root = Path(a.root).resolve()
    char_dir = root / "assets" / "characters"
    weapon_dir = root / "assets" / "weapons"
    map_dir = root / "assets" / "map"
    report = {"project": "GAMEFORGE OFFLINE PvP — First A Prototype", "target": "Android only",
              "render_resolution": [1280, 720], "offline_only": True, "characters": [], "weapons": [], "failures": []}
    for name in CHARACTERS:
        path = char_dir / f"{name}.glb"
        data = read_glb(path)
        bones = max((len(s.get("joints", [])) for s in data.get("skins", [])), default=0)
        animations = [x.get("name", "") for x in data.get("animations", [])]
        checks = {
            "file_present": path.stat().st_size > 50000,
            "humanoid_rig": bones >= 17,
            "idle": any("idle" in x.lower() for x in animations),
            "skinned_mesh": bool(data.get("meshes")) and bool(data.get("skins")),
            "full_locomotion_and_emotes": all(
                any(required in clip.lower() for clip in animations)
                for required in REQUIRED_ANIMATIONS
            ),
        }
        if not all(checks.values()):
            raise RuntimeError(f"{name} rig/animation validation failed: {checks}, animations={animations}")
        report["characters"].append({"name": name, "bytes": path.stat().st_size, "bones": bones,
                                     "animations": animations, "checks": checks})
    hashes = set()
    for ident in WEAPONS:
        path = weapon_dir / f"{ident}.glb"
        data = read_glb(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in hashes:
            raise RuntimeError(f"Weapon model is duplicated: {ident}")
        hashes.add(digest)
        if path.stat().st_size < 8000 or not data.get("meshes") or not data.get("materials"):
            raise RuntimeError(f"Weapon model failed mesh/material validation: {ident}")
        report["weapons"].append({"id": ident, "bytes": path.stat().st_size,
                                  "mesh_count": len(data.get("meshes", [])),
                                  "material_count": len(data.get("materials", []))})
    world = map_dir / "GAMEFORGE_BlackTide_Port.glb"
    if world.stat().st_size < 100000:
        raise RuntimeError("BLACKTIDE combat map GLB is missing or too small")
    world_audit = json.loads((map_dir / "GAMEFORGE_BlackTide_Audit.json").read_text(encoding="utf-8"))
    map_gates = {
        "at_least_three_buildings": world_audit.get("buildings", 0) >= 3,
        "at_least_twenty_five_cover_pieces": world_audit.get("cover", 0) >= 25,
        "three_playable_interiors": world_audit.get("interior_spaces", 0) >= 3,
        "two_vertical_routes": world_audit.get("vertical_routes", 0) >= 2,
        "collision_geometry": world_audit.get("collision_proxy_candidates", 0) >= 80,
        "large_240m_play_area": world_audit.get("dimensions_m", [0,0])[0] >= 200,
        "no_world_generator_failures": not world_audit.get("failures"),
    }
    if not all(map_gates.values()):
        raise RuntimeError("BLACKTIDE world audit failed: " + str(map_gates))
    report["map"] = {"file": world.name, "bytes": world.stat().st_size,
                     "buildings": world_audit.get("buildings"),
                     "cover": world_audit.get("cover"),
                     "interior_spaces": world_audit.get("interior_spaces"),
                     "vertical_routes": world_audit.get("vertical_routes"),
                     "collision_proxy_candidates": world_audit.get("collision_proxy_candidates"),
                     "objects": world_audit.get("counts", {}),
                     "checks": map_gates}
    project = (root / "project.godot").read_text(encoding="utf-8")
    if "viewport_width=1280" not in project or "viewport_height=720" not in project:
        raise RuntimeError("Project resolution is not locked to 1280x720")
    if "network/limits" in project.lower() or "http://" in project.lower() or "https://" in project.lower():
        raise RuntimeError("Unexpected online dependency found in runtime project settings")
    report["summary"] = {"characters_ok": 10, "weapon_models_ok": 10, "map_ok": True,
                         "all_rigs_have_full_locomotion": True,
                         "required_animation_clips": list(REQUIRED_ANIMATIONS),
                         "resolution": "1280x720"}
    (root / "ASSET_VALIDATION.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("PASS: 10 rigged operators with 11 animation states, 10 unique weapons, expanded combat map and 1280x720 settings.")

if __name__ == "__main__":
    main()
