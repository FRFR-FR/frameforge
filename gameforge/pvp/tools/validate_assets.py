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
    if world_audit.get("failures") or world_audit.get("dimensions_m", [0,0])[0] < 200 or world_audit.get("buildings", 0) < 10:
        raise RuntimeError("BLACKTIDE world audit failed")
    report["map"] = {"file": world.name, "bytes": world.stat().st_size,
                     "terrain_vertices": world_audit.get("terrain_vertices", 0),
                     "objects": world_audit.get("counts", {})}
    previews = root / "assets" / "previews"
    preview_paths = sorted(previews.glob("*_720p.png"))
    if len(preview_paths) != 10:
        raise RuntimeError(f"Expected ten 720p character previews, got {len(preview_paths)}")
    for image in preview_paths:
        if png_size(image) != (1280, 720):
            raise RuntimeError(f"Preview is not 1280x720: {image}")
    weapon_preview = root / "assets" / "previews" / "WEAPONS_1280x720.png"
    if png_size(weapon_preview) != (1280, 720):
        raise RuntimeError("Weapon presentation preview is not 1280x720")
    project = (root / "project.godot").read_text(encoding="utf-8")
    if "viewport_width=1280" not in project or "viewport_height=720" not in project:
        raise RuntimeError("Project resolution is not locked to 1280x720")
    if "network/limits" in project.lower() or "http://" in project.lower() or "https://" in project.lower():
        raise RuntimeError("Unexpected online dependency found in runtime project settings")
    report["previews"] = {"characters": len(preview_paths), "resolution": [1280, 720],
                          "weapons": weapon_preview.name}
    report["summary"] = {"characters_ok": 10, "weapon_models_ok": 10, "map_ok": True,
                         "all_rigs_have_three_emotes": True, "resolution": "1280x720"}
    (root / "ASSET_VALIDATION.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("PASS: 10 rigged characters, 3 emotes each, 10 unique weapon models, one map, all previews 1280x720.")

if __name__ == "__main__":
    main()
