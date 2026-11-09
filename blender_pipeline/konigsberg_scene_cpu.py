#!/usr/bin/env python3
"""FrameForge educational scene: The Seven Bridges of Konigsberg.

Native Blender scene built from real 3D meshes, curves, materials, lights,
camera animation and keyframes. No generated images or external assets.
"""
import bpy
import math
import os
import sys
import json
import argparse
import shutil
import subprocess
from mathutils import Vector

FPS = 24
DURATION = 20
FRAME_END = FPS * DURATION
WIDTH, HEIGHT = 720, 1280
OUT_NAME = "FrameForge_Konigsberg_20s"

ISLANDS = {
    "A": (-3.85,  2.65),
    "B": (-3.85, -2.65),
    "C": ( 3.85,  2.65),
    "D": ( 3.85, -2.65),
}
# Seven bridges, with the correct multigraph degrees A=3, B=3, C=3, D=5.
BRIDGES = [
    ("A", "B",  0.00, "AB"),
    ("A", "C",  0.00, "AC"),
    ("A", "D",  0.00, "AD"),
    ("B", "D", -0.48, "BD-1"),
    ("B", "D",  0.48, "BD-2"),
    ("C", "D", -0.48, "CD-1"),
    ("C", "D",  0.48, "CD-2"),
]
DEGREES = {"A": 3, "B": 3, "C": 3, "D": 5}

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("audit", "render"), default="render")
    parser.add_argument("--output-dir", default="output/konigsberg_20s")
    return parser.parse_args(argv)

def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights, bpy.data.fonts):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)

def set_emission(mat, color, strength):
    mat.diffuse_color = (*color[:3], 1.0)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color[:3], 1.0)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return em

def make_material(name, color, metallic=0.0, roughness=0.72, emission=None):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color[:3], 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color[:3], 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if emission:
            socket = bsdf.inputs.get("Emission") or bsdf.inputs.get("Emission Color")
            if socket:
                socket.default_value = (*emission[0][:3], 1.0)
            strength = bsdf.inputs.get("Emission Strength")
            if strength:
                strength.default_value = emission[1]
    return mat

def empty(name, location=(0, 0, 0), parent=None):
    ob = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(ob)
    ob.location = location
    if parent:
        ob.parent = parent
    return ob

def cube(name, location, dimensions, material, parent=None, bevel=0.0, rotation_z=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    ob = bpy.context.object
    ob.name = name
    ob.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.location = location
    ob.rotation_euler[2] = rotation_z
    if material:
        ob.data.materials.append(material)
    if parent:
        ob.parent = parent
        ob.location = location
    if bevel > 0:
        mod = ob.modifiers.new("Soft machined edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        ob.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    return ob

def ico(name, location, radius, material, parent=None, subdivisions=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=radius, location=(0, 0, 0))
    ob = bpy.context.object
    ob.name = name
    if material:
        ob.data.materials.append(material)
    ob.location = location
    if parent:
        ob.parent = parent
        ob.location = location
    return ob

def curve_line(name, points, bevel_depth, material, parent=None, cyclic=False):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 1
    data.bevel_depth = bevel_depth
    data.bevel_resolution = 3
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (co[0], co[1], co[2], 1.0)
    spline.use_cyclic_u = cyclic
    ob = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(ob)
    if material:
        data.materials.append(material)
    if parent:
        ob.parent = parent
    return ob

def text_object(name, body, location, size, material, parent=None, align="CENTER"):
    data = bpy.data.curves.new(name, "FONT")
    data.body = body
    data.size = size
    data.align_x = align
    data.align_y = "CENTER"
    data.extrude = 0.002
    data.bevel_depth = 0.0007
    ob = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(ob)
    ob.location = location
    if material:
        data.materials.append(material)
    if parent:
        ob.parent = parent
        ob.location = location
    return ob

def animate_emission(em_node, keys):
    strength = em_node.inputs["Strength"]
    for frame, value in keys:
        strength.default_value = value
        strength.keyframe_insert(data_path="default_value", frame=frame)

def animated_text(camera, name, body, y, size, color, start_s, end_s, subtitle=False):
    mat = bpy.data.materials.new(name + " emission")
    em = set_emission(mat, color, 0.0)
    ob = text_object(name, body, (0, y, -5.2), size, mat, parent=camera)
    start = max(1, int(start_s * FPS))
    peak = min(FRAME_END, start + 8)
    fade = min(FRAME_END, int(end_s * FPS))
    for frame, value in ((start, 0.0), (peak, 2.0 if not subtitle else 1.35),
                         (max(peak + 1, fade - 8), 2.0 if not subtitle else 1.35),
                         (fade, 0.0)):
        em.inputs["Strength"].default_value = value
        em.inputs["Strength"].keyframe_insert(data_path="default_value", frame=frame)
    ob["screen_overlay"] = True
    return ob

def make_island(name, center, radius, top_z, material):
    root = empty("LANDMASS " + name, (center[0], center[1], 0))
    n = 10
    verts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        r = radius * (0.83 + 0.16 * math.sin(i * 2.7 + (ord(name) - 64)))
        verts.append((r * math.cos(a), r * math.sin(a), top_z))
    verts.append((0, 0, top_z))
    for i in range(n):
        a = 2 * math.pi * i / n
        r = radius * (0.83 + 0.16 * math.sin(i * 2.7 + (ord(name) - 64)))
        verts.append((r * math.cos(a), r * math.sin(a), -0.18))
    faces = []
    center_index = n
    for i in range(n):
        j = (i + 1) % n
        faces.append((center_index, i, j))
        faces.append((i, n + 1 + i, n + 1 + j, j))
    mesh = bpy.data.meshes.new(name + " faceted terrain")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(material)
    mesh.update()
    land = bpy.data.objects.new(name + " island mesh", mesh)
    bpy.context.collection.objects.link(land)
    land.parent = root
    land.location = (0, 0, 0)
    land["solid_landmass"] = True
    return root

def add_windows(root, x, y, z, width, height, window_mat, prefix):
    # Warm-lit windows are separate solid meshes attached to the building.
    cols = max(1, int(width / 0.34))
    rows = max(1, int(height / 0.55))
    for row in range(rows):
        for col in range(cols):
            wx = -width * 0.32 + col * (width * 0.64 / max(1, cols - 1))
            wz = 0.22 + row * 0.48
            cube(prefix + " window", (x + wx, y - 0.18, z + wz),
                 (0.095, 0.025, 0.15), window_mat, parent=root, bevel=0.01)

def build_island_buildings(root, name, ground_mat, window_mat, roof_mat):
    layouts = [
        (-0.48, -0.08, 0.55, 0.80, 1.10),
        ( 0.40,  0.10, 0.42, 0.62, 0.82),
        (-0.08,  0.48, 0.36, 0.55, 0.72),
    ]
    for i, (x, y, w, d, h) in enumerate(layouts):
        z = 0.46 + h / 2
        b = cube(name + " building " + str(i + 1), (x, y, z),
                 (w, d, h), ground_mat, parent=root, bevel=0.035)
        b["building_type"] = "low-poly town house"
        add_windows(root, x, y, 0.46, w, h, window_mat, name)
        # A shallow roof cap gives each block a recognisable silhouette.
        cube(name + " roof " + str(i + 1), (x, y, z + h / 2 + 0.035),
             (w + 0.06, d + 0.06, 0.10), roof_mat, parent=root, bevel=0.025)

def build_bridge(edge, index, bridge_mat, gold_emission, pier_mat):
    a, b, offset, label = edge
    pa = Vector(ISLANDS[a])
    pb = Vector(ISLANDS[b])
    delta = pb - pa
    length = delta.length
    direction = delta.normalized()
    perpendicular = Vector((-direction.y, direction.x))
    start = pa + direction * 1.38 + perpendicular * offset
    finish = pb - direction * 1.38 + perpendicular * offset
    span = finish - start
    bridge_length = span.length
    angle = math.atan2(span.y, span.x)
    middle = (start + finish) * 0.5
    rig = empty("BRIDGE RIG " + label, (middle.x, middle.y, 0.58))
    rig["connects_landmasses"] = [a, b]
    rig["bridge_id"] = label
    rig["is_rigid_assembly"] = True
    deck = cube(label + " stone deck", (0, 0, 0), (bridge_length, 0.52, 0.16),
                bridge_mat, parent=rig, bevel=0.055, rotation_z=angle)
    deck["connected_to"] = [a, b]
    # Raised edge rails, transverse planks and two structural piers.
    for side in (-1, 1):
        cube(label + " parapet", (0, side * 0.245, 0.16),
             (bridge_length, 0.055, 0.18), pier_mat, parent=rig,
             bevel=0.018, rotation_z=0)
    plank_count = max(7, int(bridge_length / 0.30))
    for k in range(plank_count):
        x = -bridge_length * 0.46 + k * (bridge_length * 0.92 / max(1, plank_count - 1))
        cube(label + " paving joint", (x, 0, 0.086), (0.025, 0.43, 0.012),
             pier_mat, parent=rig, bevel=0.004)
    for p in (-0.28, 0.28):
        cube(label + " support pier", (p * bridge_length, 0, -0.30),
             (0.20, 0.22, 0.60), pier_mat, parent=rig, bevel=0.03)
    # A continuous emissive centre line carries the viewer's eye across the span.
    glow = curve_line(label + " illuminated route", [
        (-bridge_length * 0.47, 0, 0.105), (bridge_length * 0.47, 0, 0.105)
    ], 0.035, gold_emission, parent=rig)
    glow["route_edge"] = label
    return rig, glow

def build_graph(graph_root, node_mat, edge_emission, ring_emission, label_mat):
    coords = {
        "A": (-2.65,  1.72, 0.55),
        "B": (-2.65, -1.72, 0.55),
        "C": ( 2.65,  1.72, 0.55),
        "D": ( 2.65, -1.72, 0.55),
    }
    node_objects = {}
    for name, pos in coords.items():
        node = ico("GRAPH NODE " + name, pos, 0.34, node_mat, graph_root, 2)
        node["degree"] = DEGREES[name]
        node["vertex_id"] = name
        node_objects[name] = node
        # A thin torus-like ring is made from a circular bevelled curve.
        ring_pts = [(pos[0] + 0.46 * math.cos(i * 2 * math.pi / 48),
                     pos[1] + 0.46 * math.sin(i * 2 * math.pi / 48),
                     pos[2]) for i in range(48)]
        curve_line("Node " + name + " halo", ring_pts, 0.018, ring_emission,
                   parent=graph_root, cyclic=True)
        text_object("Degree " + name, str(DEGREES[name]), (pos[0], pos[1] - 0.72, pos[2] + 0.03),
                    0.44, label_mat, parent=graph_root)
    for idx, edge in enumerate(BRIDGES):
        a, b, offset, label = edge
        start = Vector(coords[a])
        finish = Vector(coords[b])
        vec = Vector((finish.x - start.x, finish.y - start.y))
        perp = Vector((-vec.y, vec.x)).normalized()
        p1 = (start.x, start.y, start.z + 0.03)
        p2 = (finish.x, finish.y, finish.z + 0.03)
        if abs(offset) > 0.001:
            p1 = (p1[0] + perp.x * offset, p1[1] + perp.y * offset, p1[2])
            p2 = (p2[0] + perp.x * offset, p2[1] + perp.y * offset, p2[2])
        line = curve_line("GRAPH EDGE " + label, [p1, p2], 0.055, edge_emission, parent=graph_root)
        line["connects_nodes"] = [a, b]
        line["edge_id"] = label
    return coords

def build_city(materials):
    water = cube("Deep midnight river basin", (0, 0, -0.38), (18.5, 12.8, 0.30),
                 materials["water"], bevel=0.12)
    water["solid_surface"] = True
    # Subtle low-poly current lines remain below the bridges.
    for i in range(9):
        y = -4.8 + i * 1.2
        pts = []
        for j in range(24):
            x = -8.5 + j * 17 / 23
            yy = y + 0.09 * math.sin(j * 0.65 + i)
            pts.append((x, yy, -0.205))
        curve_line("River current " + str(i), pts, 0.012, materials["water_glint"])
    island_roots = {}
    island_materials = [materials["land_a"], materials["land_b"], materials["land_c"], materials["land_d"]]
    for (name, center), landmat in zip(ISLANDS.items(), island_materials):
        root = make_island(name, center, 1.55, 0.34, landmat)
        root["landmass_label"] = name
        build_island_buildings(root, name, materials["houses"], materials["windows"], materials["roofs"])
        island_roots[name] = root
        # A gold locator ring marks each landmass without confusing it with a bridge.
        ring = [(1.22 * math.cos(i * 2 * math.pi / 64),
                 1.22 * math.sin(i * 2 * math.pi / 64), 0.38) for i in range(64)]
        curve_line("Shoreline inlay " + name, ring, 0.018, materials["shore"], root, True)
    # A restrained 18th-century town silhouette around the river map.
    for i in range(22):
        side = -1 if i % 2 == 0 else 1
        x = -8.3 + (i // 2) * 1.5
        y = side * (5.15 + 0.18 * (i % 3))
        h = 0.65 + ((i * 7) % 5) * 0.22
        w = 0.62 + (i % 3) * 0.12
        block = cube("Distant town block " + str(i), (x, y, -0.12 + h / 2),
                     (w, 0.8, h), materials["distant"], bevel=0.045)
        block["environment_prop"] = True
        for row in range(2):
            for col in range(2):
                cube("Distant lit window", (x - 0.16 + col * 0.28, y - 0.408,
                     0.02 + row * 0.28), (0.09, 0.025, 0.12), materials["windows"], bevel=0.008)
    # A few taller landmark silhouettes and a warmly-lit tower.
    for i, (x, y, h) in enumerate([(-7.6, 4.3, 2.2), (7.7, -4.3, 2.5), (0.0, 5.7, 1.6)]):
        cube("Old town landmark " + str(i), (x, y, h / 2 - 0.08),
             (0.72, 0.72, h), materials["landmark"], bevel=0.06)
        ico("Landmark cap " + str(i), (x, y, h + 0.12), 0.22,
            materials["gold"], subdivisions=1)
    return island_roots

def add_lighting(materials):
    world = bpy.data.worlds.new("Midnight blue atmosphere")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.006, 0.012, 0.032, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.28
    bpy.context.scene.world = world
    def area(name, location, energy, color, size):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.color = color
        data.shape = "DISK"
        data.size = size
        ob = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(ob)
        ob.location = location
        ob.rotation_euler = (math.radians(24), 0, math.radians(28))
    area("Cool moon key", (-5, -4, 11), 1800, (0.35, 0.54, 1.0), 9)
    area("Warm town fill", (6, 5, 9), 1250, (1.0, 0.62, 0.29), 8)
    area("Soft top fill", (0, 0, 14), 900, (0.43, 0.62, 1.0), 10)
    # Tiny emissive points create a night-sky depth cue.
    for i in range(85):
        x = ((i * 37) % 190 - 95) / 10
        y = ((i * 61) % 140 - 70) / 10
        if abs(x) < 4.5 and abs(y) < 3.3:
            continue
        ico("Distant star " + str(i), (x, y, 5.2 + (i % 7) * 0.17),
            0.018 + (i % 3) * 0.006, materials["star"], subdivisions=1)
    ico("Moon", (-7.7, 4.3, 5.7), 0.42, materials["moon"], subdivisions=2)

def create_camera():
    data = bpy.data.cameras.new("FrameForge cinematic camera")
    cam = bpy.data.objects.new("FrameForge cinematic camera", data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    data.lens = 48
    data.dof.use_dof = False
    return cam

def point_camera(cam, frame, location, target):
    cam.location = location
    direction = Vector(target) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert(data_path="location", frame=frame)
    cam.keyframe_insert(data_path="rotation_euler", frame=frame)

def animate_camera(cam):
    shots = [
        (1,   (0.0, -13.8, 10.5), (0.0, 0.0, 0.5)),
        (92,  (0.0, -14.6, 11.4), (0.0, 0.0, 0.45)),
        (204, (0.0, -12.0, 13.8), (0.0, 0.0, 1.5)),
        (310, (0.0, -10.8, 15.8), (0.0, 0.0, 2.3)),
        (408, (0.0, -10.5, 15.0), (0.0, 0.0, 2.4)),
        (480, (0.0, -10.0, 14.5), (0.0, 0.0, 2.5)),
    ]
    for frame, loc, target in shots:
        point_camera(cam, frame, loc, target)
    if cam.animation_data and cam.animation_data.action:
        for fcurve in cam.animation_data.action.fcurves:
            for kp in fcurve.keyframe_points:
                kp.interpolation = "BEZIER"

def add_overlay_titles(cam, mats):
    animated_text(cam, "Hook headline", "SEVEN BRIDGES. ONE ROUTE?", 1.78, 0.255,
                  (1.0, 0.80, 0.37), 0.1, 3.45)
    animated_text(cam, "Hook subtitle", "Can you cross every bridge exactly once?", 1.43, 0.125,
                  (0.82, 0.88, 1.0), 0.25, 3.45, True)
    animated_text(cam, "City headline", "KONIGSBERG  |  18TH CENTURY", 1.78, 0.235,
                  (1.0, 0.80, 0.37), 3.65, 7.45)
    animated_text(cam, "City subtitle", "Four land masses. Seven crossings.", 1.43, 0.13,
                  (0.82, 0.88, 1.0), 3.8, 7.45, True)
    animated_text(cam, "Graph headline", "TURN THE MAP INTO A GRAPH", 1.78, 0.225,
                  (1.0, 0.80, 0.37), 7.65, 12.0)
    animated_text(cam, "Graph subtitle", "Land = nodes   |   Bridges = edges", 1.43, 0.135,
                  (0.82, 0.88, 1.0), 7.85, 12.0, True)
    animated_text(cam, "Degree headline", "COUNT THE CONNECTIONS", 1.78, 0.245,
                  (1.0, 0.80, 0.37), 12.15, 16.0)
    animated_text(cam, "Degree subtitle", "3   •   3   •   3   •   5   —   all odd", 1.43, 0.15,
                  (0.95, 0.91, 0.76), 12.35, 16.0, True)
    animated_text(cam, "Rule headline", "FOUR ODD NODES = IMPOSSIBLE", 1.78, 0.205,
                  (1.0, 0.80, 0.37), 16.15, 20.0)
    animated_text(cam, "Rule subtitle", "A one-stroke route needs 0 or 2 odd nodes.", 1.43, 0.122,
                  (0.92, 0.95, 1.0), 16.35, 20.0, True)
    animated_text(cam, "Rule footer", "EULER'S BRIDGE PUZZLE", -1.88, 0.105,
                  (0.61, 0.73, 0.91), 16.4, 20.0, True)

def configure_render(scene, output_dir):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.render.fps_base = 1.0
    scene.frame_start = 1
    scene.frame_end = FRAME_END
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.render.filepath = os.path.join(output_dir, "frames", "frame_")
    scene.render.threads_mode = "FIXED"
    scene.render.threads = max(1, min(4, os.cpu_count() or 2))
    try:
        scene.view_settings.view_transform = "Standard"
        scene.view_settings.look = "Medium High Contrast"
        scene.view_settings.exposure = 0
        scene.view_settings.gamma = 1
    except Exception:
        pass
    scene.render.use_file_extension = True
    scene.render.image_settings.compression = 18
    # Gentle halation is part of the reference's luminous night aesthetic.
    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()
    layers = tree.nodes.new("CompositorNodeRLayers")
    glare = tree.nodes.new("CompositorNodeGlare")
    glare.glare_type = "FOG_GLOW"
    glare.quality = "MEDIUM"
    glare.threshold = 1.7
    glare.size = 7
    composite = tree.nodes.new("CompositorNodeComposite")
    tree.links.new(layers.outputs["Image"], glare.inputs["Image"])
    tree.links.new(glare.outputs["Image"], composite.inputs["Image"])
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(output_dir, "frames", "frame_")

def audit_scene(scene, output_dir):
    degree_check = {key: 0 for key in ISLANDS}
    for a, b, _offset, _label in BRIDGES:
        degree_check[a] += 1
        degree_check[b] += 1
    assert len(ISLANDS) == 4, "Expected four landmasses"
    assert len(BRIDGES) == 7, "Expected seven physical bridges"
    assert degree_check == DEGREES, "Graph degree sequence is incorrect: " + str(degree_check)
    assert scene.render.resolution_x == 720 and scene.render.resolution_y == 1280
    assert scene.render.fps == 24 and scene.frame_end == 480
    assert scene.render.engine == "CYCLES" and scene.cycles.device == "CPU"
    # Every bridge deck belongs to a named bridge assembly and lists both endpoints.
    bridge_rigs = [ob for ob in bpy.data.objects if ob.name.startswith("BRIDGE RIG ")]
    assert len(bridge_rigs) == 7, "Expected seven bridge rig assemblies"
    for ob in bridge_rigs:
        assert len(ob.get("connects_landmasses", [])) == 2
    # Ensure all generated object transforms are finite.
    for ob in bpy.data.objects:
        for value in (*ob.location, *ob.rotation_euler, *ob.scale):
            assert math.isfinite(float(value)), "Non-finite transform: " + ob.name
    report = {
        "status": "PASS",
        "renderer": "Blender Cycles CPU",
        "resolution": [WIDTH, HEIGHT],
        "fps": FPS,
        "duration_seconds": DURATION,
        "frames": FRAME_END,
        "islands": 4,
        "bridges": 7,
        "bridge_assemblies": len(bridge_rigs),
        "degree_sequence": [3, 3, 3, 5],
        "odd_degree_vertices": 4,
        "euler_trail_possible": False,
        "generated_objects": len(bpy.data.objects),
        "blender_version": bpy.app.version_string,
    }
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "Konigsberg_Audit.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report

def build_scene(output_dir):
    clean_scene()
    mats = {
        "water": make_material("Deep indigo water", (0.012, 0.035, 0.105), 0.30, 0.28),
        "water_glint": make_material("Water glints", (0.10, 0.26, 0.45), 0.2, 0.35, ((0.10, 0.25, 0.65), 0.5)),
        "land_a": make_material("Island slate blue", (0.12, 0.20, 0.32), 0.12, 0.82),
        "land_b": make_material("Island desaturated teal", (0.10, 0.25, 0.28), 0.10, 0.8),
        "land_c": make_material("Island midnight stone", (0.18, 0.21, 0.34), 0.12, 0.82),
        "land_d": make_material("Island blue grey", (0.17, 0.24, 0.34), 0.12, 0.82),
        "houses": make_material("Townhouse stone", (0.22, 0.28, 0.38), 0.08, 0.78),
        "roofs": make_material("Slate roofs", (0.075, 0.105, 0.17), 0.12, 0.72),
        "distant": make_material("Distant city silhouettes", (0.035, 0.06, 0.12), 0.10, 0.8),
        "landmark": make_material("Historic landmark stone", (0.15, 0.18, 0.27), 0.10, 0.78),
        "bridge": make_material("Bridge graphite stone", (0.25, 0.31, 0.42), 0.18, 0.55),
        "pier": make_material("Bridge edge dark bronze", (0.12, 0.16, 0.23), 0.38, 0.45),
        "gold": make_material("Antique brass", (0.45, 0.24, 0.065), 0.72, 0.28, ((1.0, 0.43, 0.07), 0.7)),
        "windows": make_material("Warm windows", (0.9, 0.48, 0.13), 0.1, 0.35, ((1.0, 0.43, 0.11), 2.1)),
        "shore": make_material("Shoreline glimmer", (0.45, 0.26, 0.08), 0.5, 0.35, ((1.0, 0.43, 0.08), 0.35)),
        "star": make_material("Cool starlight", (0.64, 0.75, 0.95), 0.0, 0.4, ((0.46, 0.63, 1.0), 1.1)),
        "moon": make_material("Moon glow", (0.85, 0.82, 0.68), 0.0, 0.4, ((1.0, 0.79, 0.51), 1.8)),
        "node": make_material("Graph nodes", (0.85, 0.64, 0.27), 0.35, 0.26, ((1.0, 0.48, 0.08), 1.3)),
        "graph_label": make_material("Graph degree labels", (1.0, 0.84, 0.52), 0.0, 0.4, ((1.0, 0.68, 0.24), 1.8)),
    }
    gold_em = set_emission(bpy.data.materials.new("Bridge route live gold"), (1.0, 0.46, 0.06), 0.0)
    graph_edge_em = set_emission(bpy.data.materials.new("Graph edge gold"), (1.0, 0.57, 0.12), 0.0)
    ring_em = set_emission(bpy.data.materials.new("Graph node halo"), (0.35, 0.72, 1.0), 0.0)
    label_em = set_emission(bpy.data.materials.new("Graph degree numeral"), (1.0, 0.82, 0.48), 1.8)
    # City and seven independent bridge assemblies.
    build_city(mats)
    add_lighting(mats)
    bridge_objects = []
    for idx, edge in enumerate(BRIDGES):
        rig, glow = build_bridge(edge, idx, mats["bridge"], gold_em, mats["pier"])
        bridge_objects.append((rig, glow))
        start = int((4.8 + idx * 0.44) * FPS)
        animate_emission(gold_em, [(max(1, start - 10), 0.12), (start, 2.2),
                                   (start + 28, 2.2), (start + 40, 0.5)])
    # A second, elevated representation of the same seven edges.
    graph_root = empty("GRAPH RIG | four vertices / seven edges", (0, 0, 2.4))
    graph_root["representation"] = "one node per landmass; one edge per bridge"
    graph_root.location.z = 2.4
    graph_root.keyframe_insert(data_path="location", frame=1)
    graph_root.location.z = 2.4
    graph_root.keyframe_insert(data_path="location", frame=180)
    graph_root.location.z = 4.25
    graph_root.keyframe_insert(data_path="location", frame=250)
    graph_root.location.z = 4.25
    graph_root.keyframe_insert(data_path="location", frame=FRAME_END)
    build_graph(graph_root, mats["node"], graph_edge_em, ring_em, label_em)
    animate_emission(graph_edge_em, [(1, 0.0), (180, 0.0), (205, 0.4), (250, 2.0), (FRAME_END, 2.0)])
    animate_emission(ring_em, [(1, 0.0), (180, 0.0), (215, 0.3), (255, 1.5), (FRAME_END, 1.5)])
    # A thin, connected route pulse travels along all seven edge strips in order.
    for idx, (_rig, _glow) in enumerate(bridge_objects):
        start = int((5.0 + idx * 0.46) * FPS)
        _glow.data.bevel_factor_start = 0.0
        _glow.data.bevel_factor_end = 0.0
        _glow.data.keyframe_insert(data_path="bevel_factor_end", frame=max(1, start - 1))
        _glow.data.bevel_factor_end = 1.0
        _glow.data.keyframe_insert(data_path="bevel_factor_end", frame=start + 18)
    camera = create_camera()
    animate_camera(camera)
    add_overlay_titles(camera, mats)
    scene = bpy.context.scene
    scene.frame_set(1)
    scene.render.image_settings.file_format = "PNG"
    configure_render(scene, output_dir)
    scene.frame_set(1)
    return scene

def main():
    args = parse_args()
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(os.path.join(output_dir, "frames"), exist_ok=True)
    scene = build_scene(output_dir)
    report = audit_scene(scene, output_dir)
    blend_path = os.path.join(output_dir, OUT_NAME + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print("FRAMEFORGE_AUDIT " + json.dumps(report))
    if args.mode == "audit":
        return
    scene.render.filepath = os.path.join(output_dir, "frames", "frame_")
    bpy.ops.render.render(animation=True)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to encode the MP4")
    mp4_path = os.path.join(output_dir, OUT_NAME + ".mp4")
    sequence = os.path.join(output_dir, "frames", "frame_%04d.png")
    subprocess.run([
        ffmpeg, "-y", "-framerate", str(FPS), "-start_number", "1",
        "-i", sequence, "-an", "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        mp4_path
    ], check=True)
    print("FRAMEFORGE_RENDER_COMPLETE " + mp4_path)

if __name__ == "__main__":
    main()
