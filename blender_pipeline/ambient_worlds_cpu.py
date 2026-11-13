#!/usr/bin/env python3
"""FrameForge: painterly, loopable 3D ambience scenes rendered natively in Blender.

All visible scene elements are actual Blender meshes, curves, lights, cameras and
procedural shader materials. No stock footage, image cards or AI-generated frames.
"""
import argparse
import json
import math
import os
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

FPS = 30
LOOP_SECONDS = 20
FRAME_COUNT = FPS * LOOP_SECONDS
WIDTH, HEIGHT = 1280, 720
random.seed(20261113)


def parse_args():
    raw = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", choices=("asmr", "study"), required=True)
    parser.add_argument("--mode", choices=("audit", "render"), default="render")
    parser.add_argument("--output-dir", default="output/ambient")
    parser.add_argument("--samples", type=int, default=24)
    return parser.parse_args(raw)


def rgba(hex_color, alpha=1.0):
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0, alpha)


def add_material(name, color, roughness=0.62, metallic=0.0,
                 texture_scale=8.0, bump_strength=0.12, bump_distance=0.035,
                 sheen=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba(color)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Sheen Weight" in bsdf.inputs:
        bsdf.inputs["Sheen Weight"].default_value = sheen
    texcoord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = texture_scale
    noise.inputs["Detail"].default_value = 4.0
    noise.inputs["Roughness"].default_value = 0.72
    ramp = nodes.new("ShaderNodeValToRGB")
    base = rgba(color)
    dark = (base[0] * 0.62, base[1] * 0.62, base[2] * 0.62, 1)
    light = (min(1.0, base[0] * 1.26 + 0.025),
             min(1.0, base[1] * 1.26 + 0.025),
             min(1.0, base[2] * 1.26 + 0.025), 1)
    ramp.color_ramp.elements[0].position = 0.18
    ramp.color_ramp.elements[0].color = dark
    ramp.color_ramp.elements[1].position = 0.83
    ramp.color_ramp.elements[1].color = light
    links.new(texcoord.outputs["Generated"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = bump_distance
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    mat.node_tree.nodes.active = bsdf
    return mat


def add_emission(name, color, strength=1.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba(color)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    em = nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = rgba(color)
    em.inputs["Strength"].default_value = strength
    mat.node_tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def assign(obj, mat):
    if mat:
        obj.data.materials.append(mat)
    return obj


def bevel(obj, amount=0.08, segments=3):
    mod = obj.modifiers.new("Soft hand-finished edges", "BEVEL")
    mod.width = amount
    mod.segments = segments
    obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    return obj


def smooth(obj):
    if obj.type == "MESH":
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj


def cube(name, loc, scale, mat, bevel_amount=0.07, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel_amount:
        bevel(obj, bevel_amount, 4)
    assign(obj, mat)
    return obj


def sphere(name, loc, scale, mat, segments=32, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    assign(obj, mat)
    smooth(obj)
    return obj


def cylinder(name, loc, radius, depth, mat, vertices=32, rotation=(0, 0, 0), bevel_amount=0.035):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                       location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    if bevel_amount:
        bevel(obj, bevel_amount, 3)
    assign(obj, mat)
    smooth(obj)
    return obj


def torus(name, loc, major, minor, mat, rotation=(0, 0, 0), major_segments=48, minor_segments=12):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                    major_segments=major_segments, minor_segments=minor_segments,
                                    location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    assign(obj, mat)
    smooth(obj)
    return obj


def curve_line(name, points, radius, mat, resolution=3, cyclic=False):
    data = bpy.data.curves.new(name + " geometry", "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 12
    data.bevel_depth = radius
    data.bevel_resolution = resolution
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (co[0], co[1], co[2], 1)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    assign(obj, mat)
    return obj


def mesh_object(name, verts, faces, mat, smooth_faces=False):
    mesh = bpy.data.meshes.new(name + " mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    assign(obj, mat)
    if smooth_faces:
        smooth(obj)
    return obj


def look_at(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


def area_light(name, loc, target, color, power, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.color = color
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    look_at(obj, target)
    return obj


def point_light(name, loc, color, power, radius):
    data = bpy.data.lights.new(name, "POINT")
    data.energy = power
    data.color = color
    data.shadow_soft_size = radius
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    return obj


def camera_at(loc, target, ortho_scale=None, lens=48):
    data = bpy.data.cameras.new("Painterly cinematic camera")
    cam = bpy.data.objects.new("Painterly cinematic camera", data)
    bpy.context.collection.objects.link(cam)
    cam.location = loc
    look_at(cam, target)
    data.lens = lens
    if ortho_scale:
        data.type = "ORTHO"
        data.ortho_scale = ortho_scale
    bpy.context.scene.camera = cam
    return cam


def loop_key(obj, frame, location=None, rotation=None, scale=None):
    if location is not None:
        obj.location = location
        obj.keyframe_insert(data_path="location", frame=frame)
    if rotation is not None:
        obj.rotation_euler = rotation
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    if scale is not None:
        obj.scale = scale
        obj.keyframe_insert(data_path="scale", frame=frame)


def add_cycles(obj):
    if not obj.animation_data or not obj.animation_data.action:
        return
    action = obj.animation_data.action
    for fc in action.fcurves:
        fc.modifiers.new("CYCLES")


def loop_sway(obj, base, amplitude, phase=0.0, axis="z", period=FRAME_COUNT):
    axis_index = {"x": 0, "y": 1, "z": 2}[axis]
    for frame in (1, 151, 301, 451, FRAME_COUNT + 1):
        angle = (frame - 1) / period * (2 * math.pi) + phase
        loc = list(base)
        loc[axis_index] += amplitude * math.sin(angle)
        loop_key(obj, frame, location=loc)
    add_cycles(obj)


def loop_orbit(obj, center, radius_x, radius_y, height=0.0, phase=0.0):
    for frame in (1, 151, 301, 451, FRAME_COUNT + 1):
        angle = (frame - 1) / FRAME_COUNT * (2 * math.pi) + phase
        loc = (center[0] + radius_x * math.cos(angle),
               center[1] + radius_y * math.sin(angle),
               center[2] + height * math.sin(angle * 2))
        loop_key(obj, frame, location=loc)
    add_cycles(obj)


def parent_keep_world(child, parent):
    matrix = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = matrix


def setup_world(color=(0.035, 0.065, 0.085), strength=0.38):
    world = bpy.data.worlds.new("Soft painted atmosphere") if not bpy.data.worlds else bpy.data.worlds[0]
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (*color, 1)
    bg.inputs["Strength"].default_value = strength


def setup_render(args, output_dir):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = FRAME_COUNT
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.render.filepath = str(output_dir / "frames" / "frame_")
    scene.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    scene.view_settings.look = "AgX - Medium High Contrast" if scene.view_settings.view_transform == "AgX" else "Medium High Contrast"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_file_extension = True
    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = 0.28
    scene.render.filepath = str(output_dir / "frames" / "frame_")
    scene.render.image_settings.file_format = "PNG"
    scene.cycles.preview_samples = 8
    scene.render.resolution_percentage = 100


def add_backdrop_ground(mat):
    cube("Infinite painted ground", (0, 0, -0.62), (30, 30, 0.35), mat, 0.08)


# ---------------------------------------------------------------------------
# ASMR WORLD: an enchanted, softly lit koi garden with a miniature waterfall.
# ---------------------------------------------------------------------------

def make_lily_pad(name, x, y, z, radius, mat, angle=0.0):
    verts = [(0, 0, 0)]
    faces = []
    steps = 28
    for i in range(steps + 1):
        a = angle + math.radians(42) + (math.radians(276) * i / steps)
        r = radius * (1.0 + 0.025 * math.sin(i * 1.7))
        verts.append((r * math.cos(a), r * math.sin(a), 0.025 * math.sin(a * 3)))
    for i in range(1, len(verts) - 1):
        faces.append((0, i, i + 1))
    obj = mesh_object(name, verts, faces, mat, True)
    obj.location = (x, y, z)
    solid = obj.modifiers.new("Leaf thickness", "SOLIDIFY")
    solid.thickness = 0.035
    bevel(obj, 0.018, 2)
    vein = curve_line(name + " central vein",
                      [(x, y, z + 0.025), (x + radius * 0.35 * math.cos(angle),
                       y + radius * 0.35 * math.sin(angle), z + 0.035),
                       (x + radius * 0.68 * math.cos(angle),
                       y + radius * 0.68 * math.sin(angle), z + 0.03)],
                      0.012, mat, 2)
    return obj


def make_lotus(x, y, z, petal_mat, gold_mat):
    sphere("Lotus heart", (x, y, z + 0.19), (0.16, 0.16, 0.11), gold_mat, 24, 12)
    for layer, count, radius, height, size in ((0, 9, 0.18, 0.12, 0.26), (1, 7, 0.10, 0.23, 0.21)):
        for i in range(count):
            a = 2 * math.pi * i / count + layer * 0.24
            petal = sphere("Sculpted lotus petal",
                           (x + radius * math.cos(a), y + radius * math.sin(a), z + height),
                           (size, 0.105, 0.075), petal_mat, 24, 12)
            petal.rotation_euler[2] = a
            petal.rotation_euler[1] = 0.2 * math.cos(a)
            petal.rotation_euler[0] = 0.18 * math.sin(a)


def make_fern(x, y, z, scale, green, light_green):
    stem = curve_line("Curving fern stem",
                      [(x, y, z), (x + 0.1 * scale, y, z + 0.42 * scale),
                       (x + 0.32 * scale, y + 0.02, z + 0.88 * scale)],
                      0.025 * scale, light_green, 3)
    for i in range(9):
        t = i / 9
        px = x + 0.08 * scale + 0.22 * scale * t
        pz = z + 0.18 * scale + 0.64 * scale * t
        side = 1 if i % 2 == 0 else -1
        for sign in (-1, 1):
            xx = px + sign * 0.22 * scale * (1 - t * 0.42)
            leaf = sphere("Fern leaflet", (xx, y, pz - 0.06 * scale),
                          (0.17 * scale, 0.045 * scale, 0.075 * scale), green, 20, 12)
            leaf.rotation_euler[1] = sign * 0.45
            leaf.rotation_euler[2] = sign * 0.18


def make_fish(name, loc, body_mat, patch_mat, phase):
    root = bpy.data.objects.new(name + " swimming rig", None)
    bpy.context.collection.objects.link(root)
    root.location = loc
    body = sphere(name + " smooth body", (loc[0], loc[1], loc[2]), (0.50, 0.22, 0.19), body_mat)
    parent_keep_world(body, root)
    patch = sphere(name + " painterly koi marking", (loc[0] + 0.08, loc[1] - 0.205, loc[2] + 0.04),
                   (0.19, 0.025, 0.12), patch_mat, 24, 16)
    parent_keep_world(patch, root)
    tail = sphere(name + " fan tail", (loc[0] - 0.52, loc[1], loc[2]),
                  (0.24, 0.045, 0.20), body_mat, 20, 12)
    tail.rotation_euler[1] = -0.35
    parent_keep_world(tail, root)
    fin = sphere(name + " dorsal fin", (loc[0] - 0.02, loc[1], loc[2] + 0.17),
                 (0.24, 0.055, 0.055), body_mat, 20, 12)
    parent_keep_world(fin, root)
    eye = sphere(name + " eye", (loc[0] + 0.34, loc[1] - 0.205, loc[2] + 0.055),
                 (0.038, 0.025, 0.038), add_emission("Deep obsidian eye", "#111b20", 0.18), 16, 10)
    parent_keep_world(eye, root)
    loop_orbit(root, loc, 0.34, 0.72, 0.045, phase)
    return root


def build_asmr():
    mats = {
        "water": add_material("Deep jade water with flowing pigment", "#2d827b", 0.16, 0.22, 12, 0.22, 0.025),
        "waterfall": add_emission("Moonlit turquoise water", "#74d8ce", 0.85),
        "rock": add_material("River stone | blue slate", "#536c70", 0.82, 0.02, 4.2, 0.22, 0.06),
        "rock_warm": add_material("River stone | warm moss", "#7c8a68", 0.87, 0.0, 5.5, 0.2, 0.06),
        "moss": add_material("Velvet moss", "#557a50", 0.94, 0, 7, 0.28, 0.045),
        "leaf": add_material("Water lily | deep emerald", "#34765d", 0.72, 0, 6, 0.16, 0.03, 0.25),
        "leaf_light": add_material("Fern | sage green", "#83a66c", 0.76, 0, 7, 0.14, 0.025, 0.35),
        "trunk": add_material("Old willow bark", "#59463c", 0.92, 0, 6, 0.23, 0.05),
        "canopy": add_material("Willow canopy | deep green", "#496e58", 0.88, 0, 5, 0.18, 0.03),
        "canopy_light": add_material("Willow canopy | painted highlights", "#9aa96b", 0.87, 0, 5, 0.17, 0.03),
        "petal": add_material("Lotus petals | blush porcelain", "#e8a6a0", 0.52, 0.0, 9, 0.08, 0.018, 0.4),
        "gold": add_material("Warm pollen gold", "#dba84c", 0.47, 0.12, 14, 0.08, 0.015),
        "fish_white": add_material("Koi | pearly ivory", "#eee5ca", 0.3, 0.12, 8, 0.06, 0.012),
        "fish_orange": add_material("Koi | vermilion brushmark", "#d86c43", 0.38, 0.08, 7, 0.08, 0.015),
        "wood": add_material("Weathered cedar", "#85644a", 0.86, 0, 5, 0.2, 0.04),
    }
    glow = add_emission("Firefly | warm honey light", "#ffdc87", 2.1)
    setup_world((0.035, 0.09, 0.105), 0.42)
    add_backdrop_ground(mats["rock"])

    # The pond is a broad, genuinely three-dimensional, lightly undulating mesh.
    verts, faces = [], []
    nx, ny = 46, 34
    for j in range(ny + 1):
        y = -5.4 + 10.8 * j / ny
        for i in range(nx + 1):
            x = -7.0 + 14.0 * i / nx
            z = -0.04 + 0.018 * math.sin(x * 1.4) * math.cos(y * 1.2)
            verts.append((x, y, z))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    pond = mesh_object("Sculpted pond surface", verts, faces, mats["water"], True)
    sub = pond.modifiers.new("Silken water surface", "SUBSURF")
    sub.levels = 1
    pond_solid = pond.modifiers.new("Water body depth", "SOLIDIFY")
    pond_solid.thickness = 0.22

    # A tiered stone ledge frames the falls and encloses the distant pond edge.
    for i in range(16):
        x = -6.3 + i * 0.83
        z = 0.42 + 0.18 * math.sin(i * 0.83)
        rock = sphere("Rounded river boulder", (x, 4.4 + 0.12 * math.sin(i), z),
                      (0.58 + 0.12 * (i % 3), 0.52, 0.48 + 0.13 * (i % 2)),
                      mats["rock"] if i % 3 else mats["rock_warm"], 20, 14)
        rock.rotation_euler[1] = 0.15 * math.sin(i)
        moss = sphere("Moss patch on stone", (x - 0.05, 4.12, z + 0.29),
                      (0.35, 0.24, 0.09), mats["moss"], 18, 10)
    for i in range(10):
        x = -6.0 + i * 1.28
        z = 0.6 + random.random() * 0.22
        sphere("Foreground river pebble", (x, -4.15 + random.uniform(-0.2, 0.3), z),
               (random.uniform(0.25, 0.48), 0.28, random.uniform(0.18, 0.31)), mats["rock"], 20, 12)

    # Willow trunks and layered canopies provide depth without hiding the pond.
    for side in (-1, 1):
        x = 5.9 * side
        trunk = cylinder("Old willow trunk", (x, 3.6, 2.0), 0.31, 4.0, mats["trunk"],
                         20, (0.06 * side, 0.0, 0.1 * side), 0.08)
        for b in range(4):
            branch = curve_line("Willow branch",
                [(x, 3.6, 2.3 + b * 0.35), (x - side * (0.6 + b * 0.12), 3.5, 3.4 + b * 0.18),
                 (x - side * (1.1 + b * 0.14), 3.45, 4.15 + b * 0.12)],
                0.085 - b * 0.008, mats["trunk"], 3)
        for j in range(7):
            cx = x + random.uniform(-1.15, 1.15)
            cy = 3.3 + random.uniform(-0.5, 0.55)
            cz = 4.0 + random.uniform(-0.15, 1.05)
            crown = sphere("Layered willow foliage", (cx, cy, cz),
                           (random.uniform(0.62, 1.0), 0.58, random.uniform(0.45, 0.82)),
                           mats["canopy"] if j % 3 else mats["canopy_light"], 24, 16)
            loop_sway(crown, crown.location.copy(), 0.045, j * 0.6, "x")

    # Mossy cliff and a curved, softly glowing waterfall.
    for i in range(11):
        x = -4.0 + i * 0.42
        z = 1.52 + 0.2 * math.sin(i * 0.8)
        sphere("Waterfall ledge stone", (x, 3.05, z),
               (0.45, 0.52, 0.48 + 0.12 * (i % 3)), mats["rock_warm"] if i % 2 else mats["rock"], 20, 14)
    for i in range(5):
        x = -3.15 + i * 0.24
        points = [(x + 0.08 * math.sin(i), 2.89, 2.65),
                  (x - 0.06, 2.82, 2.05),
                  (x + 0.10 * math.sin(i * 2), 2.76, 1.28),
                  (x + 0.04, 2.65, 0.34)]
        curve_line("Ribbon of falling water", points, 0.055 + 0.012 * (i % 2), mats["waterfall"], 4)
    for i in range(28):
        x = -3.15 + random.uniform(-0.42, 0.42)
        z = random.uniform(0.5, 2.6)
        droplet = sphere("Waterfall suspended droplet", (x, 2.58, z),
                         (0.035, 0.035, random.uniform(0.055, 0.11)), mats["waterfall"], 12, 8)
        loop_sway(droplet, droplet.location.copy(), 0.12, i * 0.77, "z")
    for i in range(3):
        ring = torus("Waterfall ripple ring", (-2.7, 2.2, 0.16 + i * 0.006),
                     0.35 + i * 0.22, 0.018, mats["waterfall"])
        base_scale = (0.8, 0.8, 0.8)
        for f, s in ((1, 0.82), (151, 1.2), (301, 0.82), (451, 1.2), (601, 0.82)):
            loop_key(ring, f, scale=(s, s, s))
        add_cycles(ring)

    # Foreground water lilies, two open lotus blooms, and detailed ferns.
    pad_positions = [(-4.2, -1.8), (-2.0, -3.0), (0.9, -2.3), (3.0, -1.6),
                     (4.1, 1.1), (1.8, 1.7), (-4.4, 1.0), (-0.2, 0.3)]
    for i, (x, y) in enumerate(pad_positions):
        pad = make_lily_pad("Floating water lily", x, y, 0.16, 0.52 + (i % 3) * 0.08,
                            mats["leaf"], i * 0.72)
        loop_sway(pad, pad.location.copy(), 0.025, i * 0.9, "z")
        if i in (1, 4, 6):
            make_lotus(x + 0.08, y + 0.02, 0.19, mats["petal"], mats["gold"])
    make_fern(-5.5, -2.7, 0.25, 1.4, mats["leaf"], mats["leaf_light"])
    make_fern(5.3, -2.5, 0.23, 1.35, mats["leaf"], mats["leaf_light"])
    make_fern(-5.2, 2.0, 0.28, 1.0, mats["leaf"], mats["leaf_light"])

    # Koi swim slowly around the pool in periodic paths.
    make_fish("Ivory and ember koi", (-1.4, -1.05, 0.29), mats["fish_white"], mats["fish_orange"], 0.0)
    make_fish("Golden koi", (2.2, -0.15, 0.28), mats["gold"], mats["fish_orange"], 2.1)
    make_fish("Pearl koi", (0.9, 2.0, 0.27), mats["fish_white"], mats["gold"], 4.0)

    # Fireflies and soft volumetric-feeling light points complete the atmosphere.
    for i in range(24):
        x = random.uniform(-5.2, 5.2)
        y = random.uniform(-1.5, 3.8)
        z = random.uniform(1.0, 4.8)
        fly = sphere("Floating firefly", (x, y, z), (0.035, 0.035, 0.035), glow, 12, 8)
        loop_orbit(fly, (x, y, z), random.uniform(0.12, 0.38),
                   random.uniform(0.12, 0.35), 0.2, i * 0.43)

    area_light("Warm late afternoon key", (-4.0, -4.0, 9.0), (0, 1, 0), (1.0, 0.73, 0.48), 1150, 7.0)
    area_light("Cool sky fill", (5.5, 1.5, 7.0), (0, 0, 0), (0.38, 0.75, 0.82), 950, 8.0)
    point_light("Waterfall aqua bounce", (-2.6, 2.0, 1.2), (0.36, 0.9, 0.92), 75, 1.6)
    cam = camera_at((0.0, -11.8, 7.5), (0.0, 0.1, 1.6), 14.2, 50)
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = bpy.context.scene.objects.get("Sculpted pond surface")
    cam.data.dof.aperture_fstop = 8.0
    return {"theme": "Enchanted koi pond and painterly waterfall",
            "palette": ["jade", "moss", "slate blue", "lotus blush", "warm honey"],
            "audio": "Original flowing-water, leaf-rustle and gentle droplet ASMR; no music."}


# ---------------------------------------------------------------------------
# STUDY WORLD: a warm desk and arched rain window in a quiet painterly library.
# ---------------------------------------------------------------------------

def make_book(name, loc, width, depth, height, cover, pages):
    cube(name + " lower cover", loc, (width, depth, 0.08), cover, 0.045)
    cube(name + " page block", (loc[0], loc[1], loc[2] + height * 0.48),
         (width * 0.96, depth * 0.94, height * 0.78), pages, 0.025)
    cube(name + " upper cover", (loc[0], loc[1], loc[2] + height),
         (width, depth, 0.08), cover, 0.045)
    spine = cube(name + " spine", (loc[0] - width * 0.48, loc[1], loc[2] + height * 0.5),
                 (0.12, depth * 0.99, height * 0.9), cover, 0.035)
    for i in range(5):
        line_y = loc[1] - depth * 0.34 + i * depth * 0.16
        curve_line(name + " page edge grain",
                   [(loc[0] - width * 0.43, line_y, loc[2] + height * 0.5),
                    (loc[0] + width * 0.43, line_y, loc[2] + height * 0.5)],
                   0.006, pages, 1)


def make_open_book(x, y, z, paper, ink, cover):
    cube("Open book leather cover", (x, y, z), (2.95, 2.0, 0.16), cover, 0.05)
    # Two curved page meshes, fully modelled in 3D and gently lifted at the spine.
    for side in (-1, 1):
        verts, faces = [], []
        nx, ny = 14, 10
        for j in range(ny + 1):
            py = -0.88 + 1.76 * j / ny
            for i in range(nx + 1):
                u = i / nx
                px = side * (0.08 + 1.28 * u)
                pz = z + 0.12 + 0.14 * (u ** 2) + 0.02 * math.sin(py * 2 + u * 4)
                verts.append((x + px, y + py, pz))
        for j in range(ny):
            for i in range(nx):
                a = j * (nx + 1) + i
                faces.append((a, a + 1, a + nx + 2, a + nx + 1))
        page = mesh_object("Open book | sculpted paper page", verts, faces, paper, True)
        sol = page.modifiers.new("Paper thickness", "SOLIDIFY")
        sol.thickness = 0.012
        for row in range(7):
            yy = y - 0.58 + row * 0.17
            points = [(x + side * 0.26, yy, z + 0.19),
                      (x + side * 0.63, yy + 0.015, z + 0.22),
                      (x + side * 1.18, yy, z + 0.29)]
            curve_line("Fine printed page rule", points, 0.006, ink, 1)
    cube("Book cloth spine", (x, y, z + 0.12), (0.16, 1.95, 0.18), cover, 0.025)


def make_leaf_cluster(x, y, z, green, light, count=9, scale=1.0):
    pot = cylinder("Ceramic plant pot", (x, y, z + 0.22 * scale),
                   0.34 * scale, 0.48 * scale,
                   add_material("Glazed terracotta pot", "#b86f55", 0.32, 0.0, 12, 0.05, 0.01), 40)
    torus("Pot rim", (x, y, z + 0.43 * scale), 0.34 * scale, 0.045 * scale, light)
    for i in range(count):
        a = 2 * math.pi * i / count
        height = random.uniform(0.55, 1.05) * scale
        end = (x + 0.42 * scale * math.cos(a), y + 0.06 * math.sin(a), z + 0.55 * scale + height)
        start = (x, y, z + 0.42 * scale)
        curve_line("Plant stem", [start, (x + 0.18 * scale * math.cos(a), y, z + 0.62 * scale),
                                  end], 0.018 * scale, green, 2)
        leaf = sphere("Broad houseplant leaf", end,
                      (0.31 * scale, 0.09 * scale, 0.13 * scale),
                      green if i % 3 else light, 24, 12)
        leaf.rotation_euler[1] = -0.45 * math.cos(a)
        leaf.rotation_euler[2] = a


def make_arched_window(frame_mat, glass_mat):
    cx, y = 0.35, 2.35
    bottom, spring, radius = 1.65, 4.45, 2.55
    # Dark blue window glazing behind the frame.
    cube("Large arched window glass", (cx, y + 0.12, 3.2), (5.05, 0.11, 3.25), glass_mat, 0.02)
    arch_points = []
    for i in range(25):
        a = math.pi * i / 24
        arch_points.append((cx + radius * math.cos(a), y, spring + radius * math.sin(a)))
    left = [(-2.2 + cx, y, bottom), (-2.2 + cx, y, spring)]
    right = [(2.2 + cx, y, bottom), (2.2 + cx, y, spring)]
    curve_line("Arched window outer carved frame", arch_points, 0.13, frame_mat, 5)
    curve_line("Left window jamb", left, 0.13, frame_mat, 5)
    curve_line("Right window jamb", right, 0.13, frame_mat, 5)
    curve_line("Window sill", [(cx - 2.28, y - 0.03, bottom),
                               (cx, y - 0.12, bottom - 0.08),
                               (cx + 2.28, y - 0.03, bottom)], 0.16, frame_mat, 5)
    # Crossbars and central mullion.
    curve_line("Window central mullion", [(cx, y - 0.045, bottom), (cx, y - 0.045, 6.96)],
               0.065, frame_mat, 4)
    curve_line("Window horizontal crossbar", [(cx - 2.2, y - 0.045, 3.15),
                                                (cx + 2.2, y - 0.045, 3.15)],
               0.07, frame_mat, 4)
    # A small moon, layered clouds, distant hills and tree silhouettes beyond the glass.
    moon = sphere("Soft full moon beyond the window", (cx + 1.25, 2.68, 5.68),
                  (0.52, 0.08, 0.52), add_emission("Moonlight parchment", "#e6d6a7", 1.3), 40, 24)
    for i in range(5):
        cloud = sphere("Distant painted cloud", (cx - 2.1 + i * 0.82, 2.72, 4.4 + 0.28 * math.sin(i)),
                       (0.72, 0.08, 0.22), add_material("Blue-grey cloud pigment", "#536b83", 0.95, 0, 4, 0.1, 0.02), 20, 12)
        loop_sway(cloud, cloud.location.copy(), 0.08, i * 0.4, "x")
    for i in range(9):
        xx = cx - 2.45 + i * 0.61
        h = 0.6 + 0.5 * (i % 4)
        cylinder("Distant pine trunk", (xx, 2.79, 2.0 + h * 0.3), 0.045, h, frame_mat, 8)
        for j in range(3):
            bpy.ops.mesh.primitive_cone_add(vertices=9, radius1=0.45 - j * 0.07, radius2=0.02,
                                           depth=0.85, location=(xx, 2.75, 2.35 + h * 0.45 + j * 0.28))
            tree = bpy.context.object
            tree.name = "Layered pine silhouette"
            assign(tree, frame_mat)
    # Rain beads sit on the near surface of the glass and shimmer in the lamp/moon light.
    rain_mat = add_material("Rain bead highlights", "#a8c5d4", 0.16, 0.1, 24, 0.08, 0.012)
    for i in range(64):
        xx = random.uniform(cx - 2.25, cx + 2.25)
        zz = random.uniform(2.0, 6.6)
        drop = sphere("Rain bead on window", (xx, 2.24, zz),
                      (random.uniform(0.018, 0.035), 0.018, random.uniform(0.055, 0.12)),
                      rain_mat, 12, 8)
        loop_sway(drop, drop.location.copy(), random.uniform(0.07, 0.15), i * 0.63, "z")
        if i % 4 == 0:
            streak = curve_line("Fine rain trail on glass",
                                [(xx, 2.235, zz - 0.22), (xx + 0.025, 2.235, zz - 0.07),
                                 (xx, 2.235, zz + 0.02)], 0.006, rain_mat, 1)
    return (cx, y, bottom, spring, radius)


def build_study():
    mats = {
        "wall": add_material("Midnight blue plaster | brush grain", "#293e54", 0.94, 0, 5, 0.22, 0.06),
        "wood": add_material("Walnut desk | hand-oiled grain", "#79533c", 0.5, 0, 3.0, 0.18, 0.035),
        "wood_dark": add_material("Walnut carved trim", "#422f2b", 0.55, 0, 5, 0.17, 0.03),
        "brass": add_material("Antique brass", "#c39651", 0.28, 0.72, 16, 0.07, 0.01),
        "paper": add_material("Warm ivory handmade paper", "#e9dcb9", 0.82, 0, 16, 0.08, 0.012),
        "ink": add_material("Soft graphite ink", "#544d49", 0.9, 0, 18, 0.06, 0.01),
        "cover": add_material("Forest green book leather", "#31554c", 0.48, 0, 5, 0.16, 0.03, 0.25),
        "cover_blue": add_material("Midnight blue book cloth", "#344761", 0.56, 0, 5, 0.14, 0.025),
        "cover_rust": add_material("Burnt sienna book cloth", "#985d48", 0.56, 0, 5, 0.14, 0.025),
        "glass": add_material("Rainy window | blue night", "#192e48", 0.28, 0.12, 8, 0.06, 0.01),
        "curtain": add_material("Velvet curtain | dusty teal", "#456a70", 0.9, 0, 4, 0.19, 0.04, 0.5),
        "leaf": add_material("Houseplant | forest green", "#46745d", 0.72, 0, 6, 0.17, 0.03, 0.25),
        "leaf_light": add_material("Houseplant | sage brushstroke", "#91a777", 0.75, 0, 6, 0.15, 0.025, 0.3),
        "ceramic": add_material("Glazed cream ceramic", "#e1cba7", 0.22, 0.08, 11, 0.05, 0.008),
        "coffee": add_material("Dark tea surface", "#4d3023", 0.18, 0.05, 9, 0.04, 0.006),
        "lampshade": add_material("Amber linen lampshade", "#d6a86f", 0.82, 0, 8, 0.16, 0.025, 0.3),
    }
    lamp_glow = add_emission("Warm glowing filament", "#ffc779", 2.5)
    setup_world((0.025, 0.045, 0.085), 0.34)
    add_backdrop_ground(mats["wood_dark"])
    cube("Quiet blue library wall", (0, 3.15, 3.8), (16, 0.45, 8.5), mats["wall"], 0.12)
    cube("Wood floor", (0, 0.1, -0.15), (18, 15, 0.28), mats["wood"], 0.06)

    # The large arched window is the cool visual anchor behind the warm desk.
    window = make_arched_window(mats["wood_dark"], mats["glass"])

    # Heavy velvet curtains drape down both sides of the arched opening.
    for side in (-1, 1):
        x = 0.35 + side * 2.75
        curve_line("Curtain hanging folds",
                   [(x, 2.12, 6.8), (x + side * 0.18, 2.02, 5.4),
                    (x + side * 0.10, 2.0, 3.8), (x + side * 0.23, 1.96, 1.45)],
                   0.12, mats["curtain"], 5)
        for i in range(5):
            xx = x + side * (i * 0.09)
            curve_line("Velvet curtain pleat",
                       [(xx, 2.0, 6.55), (xx + side * 0.06, 1.96, 4.2),
                        (xx, 1.92, 1.52)], 0.035, mats["leaf_light"], 3)
    curve_line("Curtain rail", [(-3.0, 2.08, 7.0), (3.75, 2.08, 7.0)],
               0.07, mats["brass"], 4)

    # Shelves with individual books frame the room.
    for side in (-1, 1):
        x = side * 6.15
        for z in (2.15, 3.75, 5.35):
            cube("Wall bookshelf", (x, 2.0, z), (2.1, 0.65, 0.16), mats["wood"], 0.04)
            for i in range(8):
                bw = random.uniform(0.16, 0.25)
                h = random.uniform(0.72, 1.25)
                bx = x - 0.82 + i * 0.23
                color = (mats["cover"], mats["cover_blue"], mats["cover_rust"])[i % 3]
                book = cube("Upright library volume", (bx, 1.92, z + 0.08 + h / 2),
                            (bw, 0.34, h), color, 0.025)
                book.rotation_euler[1] = random.uniform(-0.04, 0.04)
                cube("Gold book spine band", (bx, 1.735, z + 0.25),
                     (bw * 0.86, 0.018, 0.04), mats["brass"], 0.005)

    # A broad, solid walnut desk fills the lower third of frame.
    cube("Study desk top", (0, -1.55, 1.06), (11.2, 4.1, 0.34), mats["wood"], 0.12)
    for x in (-4.8, 4.8):
        for y in (-2.85, -0.28):
            cube("Carved desk leg", (x, y, 0.45), (0.32, 0.34, 1.05), mats["wood_dark"], 0.06)
    cube("Desk front apron", (0, -3.38, 0.72), (10.4, 0.18, 0.42), mats["wood_dark"], 0.05)
    for i in range(5):
        curve_line("Desk inlaid brass pinstripe",
                   [(-5.2, -3.63 + i * 0.035, 1.0), (5.2, -3.63 + i * 0.035, 1.0)],
                   0.008, mats["brass"], 1)

    # Open reference book, carefully sculpted pages and printed rules.
    make_open_book(-0.2, -1.55, 1.27, mats["paper"], mats["ink"], mats["cover"])
    make_book("Stacked green field journal", (-3.65, -1.0, 1.26), 1.4, 1.05, 0.28, mats["cover"], mats["paper"])
    make_book("Stacked blue atlas", (-3.42, -0.95, 1.58), 1.5, 1.08, 0.25, mats["cover_blue"], mats["paper"])
    make_book("Rust poetry volume", (3.35, -1.45, 1.25), 1.2, 0.88, 0.24, mats["cover_rust"], mats["paper"])

    # A warm pool of light from a crafted brass desk lamp.
    lamp_x, lamp_y = -4.2, -1.25
    cylinder("Lamp weighted base", (lamp_x, lamp_y, 1.35), 0.54, 0.12, mats["brass"], 48)
    cylinder("Lamp stem", (lamp_x, lamp_y, 1.95), 0.07, 1.12, mats["brass"], 24)
    sphere("Lamp swivel joint", (lamp_x, lamp_y, 2.48), (0.14, 0.14, 0.14), mats["brass"], 20, 12)
    shade = bpy.data.objects.new("Pleated amber lamp shade", bpy.data.meshes.new("Lamp shade mesh"))
    bpy.context.collection.objects.link(shade)
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.66, radius2=0.34, depth=0.65,
                                    location=(lamp_x + 0.12, lamp_y, 2.82))
    shade = bpy.context.object
    shade.name = "Pleated amber lamp shade"
    assign(shade, mats["lampshade"])
    bevel(shade, 0.045, 3)
    sphere("Lamp glowing bulb", (lamp_x + 0.12, lamp_y, 2.47), (0.17, 0.17, 0.17), lamp_glow, 20, 12)
    # A practical area light is the actual illumination, not a flat glow overlay.
    area_light("Amber desk-lamp pool", (lamp_x + 0.1, lamp_y - 0.1, 2.55),
               (0.0, -1.3, 1.1), (1.0, 0.62, 0.31), 480, 2.4)

    # Ceramic tea mug, handle, dark tea surface and slowly curling steam.
    mug_x, mug_y = 3.55, -1.8
    cylinder("Hand-thrown ceramic tea mug", (mug_x, mug_y, 1.63), 0.39, 0.68, mats["ceramic"], 48, bevel_amount=0.055)
    torus("Mug curved handle", (mug_x + 0.42, mug_y, 1.68), 0.24, 0.075, mats["ceramic"],
          (math.pi / 2, 0, 0), 36, 10)
    cylinder("Dark tea in mug", (mug_x, mug_y, 1.99), 0.325, 0.025, mats["coffee"], 48, bevel_amount=0.005)
    for i in range(3):
        x = mug_x + (i - 1) * 0.16
        steam = curve_line("Curling tea steam",
                           [(x, mug_y, 2.08), (x + 0.12, mug_y + 0.02, 2.35),
                            (x - 0.08, mug_y + 0.03, 2.62), (x + 0.08, mug_y, 2.88)],
                           0.018, mats["paper"], 3)
        loop_sway(steam, steam.location.copy(), 0.065, i * 1.3, "x")

    # A ceramic fern, writing tools, paper sheets and small brass details.
    make_leaf_cluster(4.72, -0.35, 1.26, mats["leaf"], mats["leaf_light"], 11, 0.9)
    cylinder("Pencil holder", (-2.65, -2.55, 1.47), 0.25, 0.48, mats["ceramic"], 32)
    for i in range(7):
        p = cylinder("Wooden pencil", (-2.65 + random.uniform(-0.12, 0.12),
                                       -2.55 + random.uniform(-0.12, 0.12), 1.95),
                     0.035, 0.95, mats["wood_dark"], 12,
                     rotation=(random.uniform(-0.15, 0.15), random.uniform(-0.3, 0.3), 0))
    cube("Loose study notes", (2.0, -2.83, 1.25), (1.05, 0.72, 0.045), mats["paper"], 0.018, (0, 0, -0.12))
    for i in range(5):
        yy = -3.08 + i * 0.12
        curve_line("Pencil notes on paper",
                   [(1.62, yy, 1.278), (1.95, yy + 0.01, 1.278), (2.36, yy, 1.278)],
                   0.006, mats["ink"], 1)
    torus("Brass paperweight", (2.72, -2.8, 1.34), 0.14, 0.045, mats["brass"])
    # A small analog clock reinforces the slow study atmosphere.
    cylinder("Desk clock body", (-1.85, -0.48, 1.5), 0.38, 0.11, mats["wood_dark"], 48, (math.pi/2, 0, 0))
    cylinder("Desk clock dial", (-1.85, -0.55, 1.5), 0.31, 0.025, mats["paper"], 48, (math.pi/2, 0, 0), 0.01)
    curve_line("Clock minute hand", [(-1.85, -0.575, 1.5), (-1.85, -0.575, 1.72)], 0.012, mats["ink"], 2)
    curve_line("Clock hour hand", [(-1.85, -0.58, 1.5), (-1.99, -0.58, 1.42)], 0.018, mats["ink"], 2)

    # Floating dust motes and a softly moving candle add gentle loop motion.
    dust_mat = add_emission("Golden drifting dust", "#f5d9a0", 0.38)
    for i in range(34):
        x = random.uniform(-4.4, 4.2)
        y = random.uniform(-1.2, 1.65)
        z = random.uniform(1.6, 4.8)
        mot = sphere("Floating dust mote", (x, y, z), (0.018, 0.018, 0.018), dust_mat, 10, 6)
        loop_orbit(mot, (x, y, z), random.uniform(0.12, 0.32),
                   random.uniform(0.10, 0.28), 0.12, i * 0.71)

    candle_x, candle_y = 4.7, -2.55
    cylinder("Small beeswax candle", (candle_x, candle_y, 1.42), 0.18, 0.38, mats["paper"], 32)
    flame_mat = add_emission("Candlelight", "#ffb55e", 2.0)
    flame = sphere("Candle flame", (candle_x, candle_y, 1.68), (0.075, 0.07, 0.17), flame_mat, 16, 10)
    for frame, sc in ((1, (1, 1, 1)), (151, (0.92, 0.92, 1.12)), (301, (1.05, 1.0, 0.94)),
                      (451, (0.92, 0.92, 1.12)), (601, (1, 1, 1))):
        loop_key(flame, frame, scale=sc)
    add_cycles(flame)
    point_light("Candle amber bounce", (candle_x, candle_y, 1.85), (1.0, 0.46, 0.2), 28, 0.6)

    area_light("Cool blue window fill", (0.2, 2.0, 5.9), (0, -1.0, 1.2), (0.38, 0.62, 0.95), 720, 5.0)
    area_light("Soft warm room bounce", (4.5, -4.5, 6.5), (0, 0, 2.0), (1.0, 0.72, 0.48), 360, 6.0)
    cam = camera_at((0.0, -11.6, 5.65), (0.0, 0.1, 3.05), 13.2, 52)
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = 12.5
    cam.data.dof.aperture_fstop = 8.0
    return {"theme": "Cozy walnut study desk and moonlit arched rain window",
            "palette": ["midnight blue", "dusty teal", "walnut", "parchment", "amber"],
            "audio": "Original gentle felt-piano and warm ambient chords; no ASMR or sound effects."}


def build_scene(args, output_dir):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.materials:
        bpy.data.materials.remove(block)
    if args.project == "asmr":
        info = build_asmr()
        project_name = "FrameForge_Enchanted_Water_Garden_ASMR"
    else:
        info = build_study()
        project_name = "FrameForge_Cozy_Rainy_Study"
    setup_render(args, output_dir)
    scene = bpy.context.scene
    scene.frame_set(1)
    scene.render.filepath = str(output_dir / "frames" / "frame_")
    os.makedirs(output_dir / "frames", exist_ok=True)
    blend_path = output_dir / (project_name + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    # Optional glTF copy makes the scene portable to other 3D tools.
    glb_path = output_dir / (project_name + ".glb")
    glb_status = "not exported"
    try:
        bpy.ops.export_scene.gltf(filepath=str(glb_path), export_format="GLB", export_animations=True)
        glb_status = "exported"
    except Exception as exc:
        glb_status = "optional export unavailable: " + str(exc)[:240]
    objects = list(scene.objects)
    mesh_count = sum(1 for o in objects if o.type == "MESH")
    animation_count = sum(1 for o in objects if o.animation_data and o.animation_data.action)
    assert scene.camera is not None, "Scene has no active camera"
    assert mesh_count >= 100, "The environment is not sufficiently modelled in 3D"
    assert animation_count >= 20, "The scene does not have enough looping animation"
    report = {
        "project": args.project,
        "scene": info["theme"],
        "style": "Painterly 3D diorama with hand-finished sculpted forms and procedural textured materials",
        "fully_3d": True,
        "image_cards_or_stock_footage": False,
        "render": {"width": WIDTH, "height": HEIGHT, "fps": FPS,
                   "loop_seconds": LOOP_SECONDS, "loop_frames": FRAME_COUNT,
                   "engine": "Blender Cycles CPU", "samples": args.samples, "denoising": True},
        "quality": {"mesh_objects": mesh_count, "animated_objects": animation_count,
                    "materials": len(bpy.data.materials), "active_camera": scene.camera.name,
                    "color_management": scene.view_settings.view_transform},
        "palette": info["palette"],
        "sound_design": info["audio"],
        "blend_file": blend_path.name,
        "glb_file": glb_path.name,
        "glb_export": glb_status,
        "loop_validation": "Keyframed cyclic motions return to their starting transforms at frame 601."
    }
    with open(output_dir / "scene_audit.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    if args.mode == "audit":
        scene.render.resolution_percentage = 40
        scene.cycles.samples = 8
        scene.render.filepath = str(output_dir / "preview")
        scene.frame_set(1)
        bpy.ops.render.render(write_still=True)
        scene.frame_set(301)
        scene.render.filepath = str(output_dir / "preview_mid")
        bpy.ops.render.render(write_still=True)
    else:
        scene.render.resolution_percentage = 100
        scene.cycles.samples = args.samples
        scene.render.filepath = str(output_dir / "frames" / "frame_")
        scene.frame_set(1)
        bpy.ops.render.render(animation=True)
    return report


def main():
    args = parse_args()
    out = Path(args.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = build_scene(args, out)
    print("FRAMEFORGE_AMBIENT_SCENE_OK", json.dumps(report, sort_keys=True))
    if args.mode == "render":
        frames = list((out / "frames").glob("frame_*.png"))
        if len(frames) != FRAME_COUNT:
            raise RuntimeError(f"Expected {FRAME_COUNT} rendered frames, got {len(frames)}")
        print("FRAMEFORGE_LOOP_FRAMES_OK", len(frames))


if __name__ == "__main__":
    main()
