#!/usr/bin/env python3
"""Author ten original stylised game weapons in Blender and export audited GLB models."""
from __future__ import annotations
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

WEAPONS = [
    ("Vesper9", "VESPER-9", "sidearm", (0.08, 0.76, 0.82), 0.82, 1.6, "compact"),
    ("FluxSMG", "FLUX SMG", "smg", (0.27, 0.82, 0.56), 0.92, 2.0, "fast"),
    ("AegisAR", "AEGIS AR", "assault", (0.22, 0.55, 0.96), 1.00, 2.2, "balanced"),
    ("KestrelBurst", "KESTREL BURST", "burst", (0.95, 0.58, 0.18), 1.02, 2.1, "three-round"),
    ("RangerDMR", "RANGER DMR", "dmr", (0.72, 0.78, 0.88), 1.15, 2.4, "precision"),
    ("Longbow", "LONGBOW", "sniper", (0.86, 0.37, 0.28), 1.25, 2.8, "long-range"),
    ("Breach12", "BREACH-12", "shotgun", (0.83, 0.72, 0.36), 1.18, 2.0, "close-range"),
    ("BastionLMG", "BASTION LMG", "lmg", (0.61, 0.42, 0.88), 1.40, 2.5, "support"),
    ("PulseCarbine", "PULSE CARBINE", "energy", (0.14, 0.91, 0.96), 0.98, 2.3, "pulse"),
    ("ArcLance", "ARC LANCE", "rail", (0.96, 0.34, 0.62), 1.22, 2.7, "charged"),
]

def args():
    raw = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True)
    p.add_argument("--preview", required=True)
    return p.parse_args(raw)

def material(name, color, metallic=0.2, roughness=0.38, emission=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        socket = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        if socket:
            socket.default_value = (*color, 1)
        strength = bsdf.inputs.get("Emission Strength")
        if strength:
            strength.default_value = emission
    return m

def box(col, name, loc, size, mat, bevel=0.035):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    if bevel:
        mod = o.modifiers.new("Machined edge bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        o.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    for old in list(o.users_collection):
        old.objects.unlink(o)
    col.objects.link(o)
    return o

def cylinder(col, name, loc, radius, length, mat, vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=length,
                                       location=loc, rotation=(0, math.pi / 2, 0))
    o = bpy.context.object
    o.name = name
    o.data.materials.append(mat)
    for old in list(o.users_collection):
        old.objects.unlink(o)
    col.objects.link(o)
    return o

def make_weapon(spec, palette):
    ident, label, kind, accent_rgb, length, width, role = spec
    col = bpy.data.collections.new(f"WEAPON | {label}")
    bpy.context.scene.collection.children.link(col)
    dark, metal, accent, light = palette
    accent = material(f"{label} | anodised signature", accent_rgb, 0.66, 0.27, 0.08)
    barrel_len = 0.48 * length
    receiver_len = 0.70 * length
    box(col, f"{ident}_Receiver", (0.15 * length, 0, 0.0), (receiver_len, width, 0.24 * width), dark, 0.055)
    box(col, f"{ident}_UpperRail", (0.14 * length, 0, 0.15 * width), (receiver_len * 0.88, width * 0.34, 0.05 * width), metal, 0.018)
    box(col, f"{ident}_SidePanel", (0.18 * length, -0.53 * width, 0.0), (receiver_len * 0.46, 0.025, 0.12 * width), accent, 0.015)
    cylinder(col, f"{ident}_Barrel", (0.72 * length, 0, 0.02 * width), 0.052 * width / 0.2, barrel_len, metal)
    cylinder(col, f"{ident}_Muzzle", (0.72 * length + barrel_len / 2, 0, 0.02 * width), 0.075 * width / 0.2, 0.13, accent)
    box(col, f"{ident}_Grip", (-0.10 * length, -0.025, -0.24 * width), (0.22 * length, width * 0.78, 0.40 * width), dark, 0.045)
    box(col, f"{ident}_TriggerGuard", (0.10 * length, -0.03, -0.16 * width), (0.22 * length, 0.035, 0.10 * width), accent, 0.018)

    if kind in ("sidearm", "smg"):
        box(col, f"{ident}_Magazine", (0.18 * length, 0.02, -0.27 * width), (0.20 * length, width * 0.55, 0.30 * width), accent, 0.04)
        if kind == "smg":
            box(col, f"{ident}_FoldingStock", (-0.43 * length, 0.0, 0.02 * width), (0.32 * length, width * 0.22, 0.09 * width), metal, 0.025)
            cylinder(col, f"{ident}_Foregrip", (0.42 * length, 0, -0.21 * width), 0.075, 0.32, dark)
    else:
        stock_len = 0.36 * length if kind not in ("sniper", "lmg") else 0.52 * length
        box(col, f"{ident}_ShoulderStock", (-0.48 * length, 0, 0.02 * width), (stock_len, width * 0.68, 0.18 * width), metal, 0.05)
        mag_len = 0.34 * length if kind in ("lmg", "shotgun") else 0.22 * length
        box(col, f"{ident}_Magazine", (0.12 * length, 0.015, -0.27 * width), (0.20 * length, width * 0.62, mag_len), accent, 0.04)
        if kind in ("dmr", "sniper"):
            cylinder(col, f"{ident}_ScopeTube", (0.20 * length, 0.0, 0.27 * width), 0.07, 0.42, dark)
            for x in (0.02 * length, 0.38 * length):
                cylinder(col, f"{ident}_ScopeRing", (x, 0, 0.27 * width), 0.10, 0.065, accent)
        elif kind == "shotgun":
            cylinder(col, f"{ident}_SecondBarrel", (0.73 * length, 0.10, -0.07 * width), 0.045, barrel_len, accent)
            cylinder(col, f"{ident}_TubeMagazine", (0.60 * length, 0.09, -0.18 * width), 0.07, barrel_len * 0.8, metal)
        elif kind == "lmg":
            cylinder(col, f"{ident}_DrumMag", (0.15 * length, 0.05, -0.28 * width), 0.20, 0.18, accent)
            box(col, f"{ident}_BipodLeft", (0.68 * length, -0.12, -0.27 * width), (0.05, 0.05, 0.32), metal, 0.01)
            box(col, f"{ident}_BipodRight", (0.68 * length, 0.12, -0.27 * width), (0.05, 0.05, 0.32), metal, 0.01)
        else:
            box(col, f"{ident}_Handguard", (0.52 * length, 0, 0.0), (0.38 * length, width * 1.13, 0.19 * width), dark, 0.035)
    if kind in ("energy", "rail"):
        box(col, f"{ident}_PowerCore", (0.12 * length, 0.0, 0.24 * width), (0.32 * length, width * 0.70, 0.16 * width), accent, 0.04)
        cylinder(col, f"{ident}_EmitterRing", (0.98 * length, 0, 0.02 * width), 0.13, 0.10, light)
        box(col, f"{ident}_EnergyWindow", (0.16 * length, -0.02, 0.34 * width), (0.20 * length, 0.025, 0.08 * width), light, 0.02)
    if kind == "burst":
        for x in (-0.02, 0.08, 0.18):
            cylinder(col, f"{ident}_BurstPort_{x}", (0.90 * length, x, 0.02 * width), 0.042, 0.12, accent, 16)
    for x in (-0.32, -0.12, 0.18, 0.40):
        cylinder(col, f"{ident}_Fastener_{x}", (x * length, -0.53 * width, 0.065 * width), 0.018, 0.025, light, 12)
    box(col, f"{ident}_ModelBadge", (0.18 * length, -0.56 * width, 0.08 * width), (0.25 * length, 0.025, 0.045), accent, 0.008)
    return col

def main():
    a = args()
    out = Path(a.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for c in list(bpy.data.collections):
        if c.name != "Collection":
            bpy.data.collections.remove(c)
    dark = material("Graphite ceramic", (0.025, 0.045, 0.065), 0.45, 0.29)
    metal = material("Brushed titanium", (0.34, 0.42, 0.48), 0.82, 0.22)
    neutral = material("Neutral alloy", (0.16, 0.22, 0.27), 0.63, 0.31)
    light = material("Cool status light", (0.56, 0.86, 0.91), 0.35, 0.2, 1.6)
    palette = (dark, metal, neutral, light)
    audit = {"weapons": [], "preview_resolution": [1280, 720], "failures": []}
    collections = []
    for spec in WEAPONS:
        col = make_weapon(spec, palette)
        collections.append(col)
        ident, label = spec[0], spec[1]
        bpy.ops.object.select_all(action="DESELECT")
        selected = list(col.objects)
        for obj in selected:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = selected[0]
        target = out / f"{ident}.glb"
        bpy.ops.export_scene.gltf(filepath=str(target), export_format="GLB", use_selection=True,
                                  export_apply=True, export_materials="EXPORT",
                                  export_cameras=False, export_lights=False)
        if not target.is_file() or target.stat().st_size < 8000:
            raise RuntimeError(f"Weapon export failed: {ident}")
        audit["weapons"].append({"id": ident, "name": label, "file": target.name, "bytes": target.stat().st_size})

    # Purpose-built 10-weapon presentation render, output fixed to 1280x720.
    stage_mat = material("Gallery stage", (0.018, 0.035, 0.055), 0.82, 0.12)
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -1.0))
    floor = bpy.context.object
    floor.name = "Weapon gallery stage"
    floor.data.materials.append(stage_mat)
    # Arrange two deliberate rows with the same authored models.
    for index, col in enumerate(collections):
        row, slot = divmod(index, 5)
        center_x = (slot - 2) * 4.7
        center_y = (0.0, 5.0)[row]
        for obj in col.objects:
            obj.location.x += center_x
            obj.location.y += center_y
            obj.location.z += 1.0
    bpy.ops.object.camera_add(location=(0, -17, 12))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 27
    camera.rotation_euler = (Vector((0, 2.3, 0.0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = camera
    bpy.ops.object.light_add(type="AREA", location=(0, -4, 9))
    key = bpy.context.object
    key.data.energy = 2600
    key.data.shape = "DISK"
    key.data.size = 12
    key.rotation_euler = (Vector((0, 1, 0)) - key.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.light_add(type="AREA", location=(0, 10, 7))
    fill = bpy.context.object
    fill.data.energy = 1700
    fill.data.size = 10
    fill.rotation_euler = (Vector((0, 2, 0)) - fill.location).to_track_quat("-Z", "Y").to_euler()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.world.color = (0.025, 0.04, 0.065)
    scene.render.filepath = str(Path(a.preview).resolve())
    bpy.ops.render.render(write_still=True)
    if not Path(a.preview).is_file() or Path(a.preview).stat().st_size < 20000:
        raise RuntimeError("Weapon gallery preview did not render")
    audit["gallery_preview"] = {"file": Path(a.preview).name, "bytes": Path(a.preview).stat().st_size}
    if len(audit["weapons"]) != 10:
        raise RuntimeError("Expected exactly ten unique weapon models")
    (out / "WEAPON_AUDIT.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print("Authored and exported ten unique, detailed weapon GLBs.")

if __name__ == "__main__":
    main()
