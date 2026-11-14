#!/usr/bin/env python3
"""Build a deterministic, painterly GAMEFORGE landscape in Blender."""
from __future__ import annotations
import argparse
import json
import math
import random
from pathlib import Path
import bpy
from mathutils import Vector

STYLE = "LOOMWILD"
WORLD_SIZE = 110.0
WIDTH, HEIGHT = 1280, 720
COUNTS = {"trees": 0, "rocks": 0, "flowers": 0, "landmarks": 0, "paths": 0}
ARGS = None

def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="build/gameforge_world")
    parser.add_argument("--seed", type=int, default=42017)
    parser.add_argument("--grid", type=int, default=129)
    parser.add_argument("--samples", type=int, default=32)
    values, _ = parser.parse_known_args()
    values.grid = max(33, min(257, values.grid))
    if values.grid % 2 == 0:
        values.grid += 1
    return values

def material(name, color, roughness=0.82, metallic=0.0, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    if emission:
        socket = shader.inputs.get("Emission Color") or shader.inputs.get("Emission")
        if socket:
            socket.default_value = (*color, 1.0)
        strength = shader.inputs.get("Emission Strength")
        if strength:
            strength.default_value = emission
    return mat

def collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col

def link_to(obj, col):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)
    return obj

def river_z(x):
    return 10.0 * math.sin(x * 0.105) + 3.0 * math.sin(x * 0.24 + 0.6)

def terrain_height(x, z):
    broad = (
        0.50 * math.sin(x * 0.047 + 0.8) * math.cos(z * 0.052)
        + 0.24 * math.sin(x * 0.105 + z * 0.041)
        + 0.15 * math.cos(z * 0.137 - x * 0.063)
        + 0.10 * math.sin((x + z) * 0.23) * math.cos((x - z) * 0.19)
    )
    ridge = 1.7 * math.exp(-((z - 34.0 - 7.0 * math.sin(x * 0.08)) / 13.0) ** 2)
    river_cut = 2.7 * math.exp(-((z - river_z(x)) / 5.3) ** 2)
    return max(0.25, 3.1 + broad * 4.2 + ridge - river_cut)

def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()

def add_terrain(col, mats, size, grid):
    vertices, faces = [], []
    step, half = size / (grid - 1), size / 2
    for iz in range(grid):
        z = -half + iz * step
        for ix in range(grid):
            x = -half + ix * step
            vertices.append((x, terrain_height(x, z), z))
    for iz in range(grid - 1):
        for ix in range(grid - 1):
            a = iz * grid + ix
            b = (iz + 1) * grid + ix
            faces.append((a, b, b + 1, a + 1))
    mesh = bpy.data.meshes.new(f"Loomwild terrain | {grid}x{grid}")
    mesh.from_pydata(vertices, [], faces)
    for mat in mats:
        mesh.materials.append(mat)
    mesh.update()
    obj = bpy.data.objects.new("WORLD_TERRAIN_Heightfield", mesh)
    col.objects.link(obj)
    for poly in mesh.polygons:
        slope = 1.0 - max(0.0, poly.normal.y)
        h = poly.center.y
        poly.material_index = 2 if slope > 0.30 or h > 7.6 else (1 if h < 2.0 else 0)
    solid = obj.modifiers.new("Terrain thickness", "SOLIDIFY")
    solid.thickness = 1.2
    obj["gameforge_world_role"] = "walkable_terrain"
    obj["grid_resolution"] = grid
    obj["world_seed"] = ARGS.seed
    return obj

def add_cone(name, location, radius, depth, mat, col, vertices=9):
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius, radius2=0.0,
                                    depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return link_to(obj, col)

def add_ico(name, location, scale, mat, col, subdivisions=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return link_to(obj, col)

def add_curve(name, points, bevel_depth, mat, col, resolution=2):
    curve = bpy.data.curves.new(name + " | spline", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 16
    curve.bevel_depth = bevel_depth
    curve.bevel_resolution = resolution
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, coord in zip(spline.points, points):
        point.co = (*coord, 1.0)
    obj = bpy.data.objects.new(name, curve)
    col.objects.link(obj)
    obj.data.materials.append(mat)
    return obj

def add_river(col, water_mat, bank_mat):
    points = [(x, 0.88, river_z(x)) for x in (-54.0 + i * 0.9 for i in range(121))]
    river = add_curve("WORLD_RIVER | winding blue-green water", points, 1.35, water_mat, col, 4)
    river["gameforge_world_role"] = "waterway"
    rng = random.Random(ARGS.seed + 2)
    for index in range(0, 121, 8):
        x, z = -54.0 + index * 0.9, river_z(-54.0 + index * 0.9)
        for side in (-1, 1):
            add_ico(
                f"Riverbank stone {index:03d}",
                (x, terrain_height(x, z + side * 2.3) + 0.12, z + side * 2.3),
                (rng.uniform(0.35, 0.8), rng.uniform(0.28, 0.55), rng.uniform(0.35, 0.75)),
                bank_mat, col, 1
            )
    return river

def add_path(col, path_mat):
    points = []
    for i in range(61):
        t = i / 60.0
        x = -51.0 + t * 91.0
        z = -24.0 + 15.0 * math.sin(t * math.pi * 1.65) + 4.0 * math.sin(t * 8.0)
        points.append((x, terrain_height(x, z) + 0.18, z))
    obj = add_curve("WORLD_PATH | old ochre trail", points, 0.56, path_mat, col, 3)
    obj["gameforge_world_role"] = "walkable_trail"
    COUNTS["paths"] += 1

def add_tree(x, z, col, rng, trunk_mat, leaf_mats):
    ground, height = terrain_height(x, z), rng.uniform(4.3, 8.0)
    radius = rng.uniform(1.25, 2.25)
    bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=radius * 0.12,
                                        depth=height * 0.43,
                                        location=(x, ground + height * 0.215, z))
    trunk = bpy.context.object
    trunk.name = "TREE_Trunk"
    trunk.data.materials.append(trunk_mat)
    link_to(trunk, col)
    leaf = leaf_mats[rng.randrange(len(leaf_mats))]
    add_cone("TREE_Canopy lower", (x, ground + height * 0.48, z), radius, height * 0.60, leaf, col, 10)
    add_cone("TREE_Canopy upper", (x, ground + height * 0.70, z), radius * 0.72, height * 0.53, leaf, col, 10)
    COUNTS["trees"] += 1

def add_rock(x, z, col, rng, mats):
    scale = rng.uniform(0.35, 1.45)
    rock = add_ico(
        "WORLD_Rock | weathered",
        (x, terrain_height(x, z) + scale * 0.42, z),
        (scale * rng.uniform(0.8, 1.5), scale * rng.uniform(0.55, 0.95),
         scale * rng.uniform(0.8, 1.35)),
        mats[rng.randrange(len(mats))], col, 2
    )
    rock.rotation_euler = (rng.uniform(-0.4, 0.4), rng.random() * math.tau, rng.uniform(-0.4, 0.4))
    COUNTS["rocks"] += 1

def add_flower_cluster(x, z, col, rng, stem_mat, flower_mats):
    y = terrain_height(x, z)
    for j in range(5):
        a = j * math.tau / 5
        px, pz = x + math.cos(a) * 0.24, z + math.sin(a) * 0.24
        bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6, radius=0.1,
                                             location=(px, y + 0.25, pz))
        obj = bpy.context.object
        obj.name = "FLOWER_Petal"
        obj.scale = (0.12, 0.07, 0.20)
        obj.data.materials.append(flower_mats[j % len(flower_mats)])
        link_to(obj, col)
    add_curve("FLOWER_Stem", [(x, y, z), (x + 0.05, y + 0.23, z)], 0.025, stem_mat, col, 1)
    COUNTS["flowers"] += 1

def add_ruin(col, stone, accent):
    x, z = 29.0, 18.0
    y = terrain_height(x, z)
    for side in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x + side * 2.5, y + 2.0, z))
        pillar = bpy.context.object
        pillar.name = "LANDMARK_Ruin_Pillar"
        pillar.dimensions = (1.05, 4.0, 1.05)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        pillar.data.materials.append(stone)
        bevel = pillar.modifiers.new("Eroded corners", "BEVEL")
        bevel.width, bevel.segments = 0.16, 3
        link_to(pillar, col)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y + 4.0, z))
    lintel = bpy.context.object
    lintel.name = "LANDMARK_Ruin_Lintel"
    lintel.dimensions = (6.8, 0.9, 1.3)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    lintel.data.materials.append(stone)
    lintel.rotation_euler.z = 0.07
    link_to(lintel, col)
    add_ico("LANDMARK_Rune_Heart", (x, y + 4.7, z - 0.12), (0.35, 0.55, 0.35), accent, col, 2)
    COUNTS["landmarks"] += 1

def add_environment(col, mats, seed):
    rng = random.Random(seed)
    tree_trunk, leaf_mats, rock_mats, flower_mats, stem_mat = mats
    for _ in range(78):
        x, z = rng.uniform(-51, 51), rng.uniform(-51, 51)
        if abs(z - river_z(x)) < 7.5 or (x < -30 and abs(z) < 12):
            continue
        add_tree(x, z, col, rng, tree_trunk, leaf_mats)
    for _ in range(105):
        x, z = rng.uniform(-52, 52), rng.uniform(-52, 52)
        if abs(z - river_z(x)) < 4.0:
            continue
        add_rock(x, z, col, rng, rock_mats)
    for _ in range(32):
        x, z = rng.uniform(-42, 42), rng.uniform(-42, 42)
        if abs(z - river_z(x)) < 5.0:
            continue
        add_flower_cluster(x, z, col, rng, stem_mat, flower_mats)

def setup_lighting(col):
    world = bpy.data.worlds.new("Loomwild | misted apricot sky")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.22, 0.33, 0.39, 1.0)
    bg.inputs["Strength"].default_value = 0.48
    bpy.context.scene.world = world
    bpy.ops.object.light_add(type="SUN", location=(0, 30, 25))
    sun = bpy.context.object
    sun.name = "LIGHT_Sunrise"
    sun.data.energy = 2.0
    sun.data.angle = math.radians(18)
    sun.data.color = (1.0, 0.79, 0.58)
    look_at(sun, (0, 0, 0))
    link_to(sun, col)
    for name, loc, target, power, color, size in (
        ("LIGHT_Warm key", (5, -18, 30), (0, 2, 0), 1800, (1.0, 0.72, 0.48), 18),
        ("LIGHT_Cool fill", (-28, -8, 18), (0, 1, 0), 1250, (0.42, 0.70, 1.0), 16),
    ):
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.name = name
        light.data.energy, light.data.shape, light.data.size, light.data.color = power, "DISK", size, color
        look_at(light, target)
        link_to(light, col)

def setup_camera(col):
    bpy.ops.object.camera_add(location=(31, -61, 37))
    camera = bpy.context.object
    camera.name = "CAMERA_Loomwild_hero"
    camera.data.lens = 48
    camera.data.dof.use_dof = True
    camera.data.dof.focus_distance = 58
    camera.data.dof.aperture_fstop = 8.0
    look_at(camera, (0, 2.0, 0))
    bpy.context.scene.camera = camera
    link_to(camera, col)

def main():
    global ARGS
    ARGS = arguments()
    output = Path(ARGS.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    COUNTS.update({"trees": 0, "rocks": 0, "flowers": 0, "landmarks": 0, "paths": 0})
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    terrain_col = collection("01 | Terrain and water")
    vegetation_col = collection("02 | Trees, stones and flora")
    structure_col = collection("03 | Landmarks and trails")
    light_col = collection("04 | Lighting and camera")

    grass = material("Meadow | deep sage", (0.16, 0.30, 0.20))
    moss = material("Meadow | river moss", (0.095, 0.20, 0.16))
    stone = material("Cliff | warm slate", (0.29, 0.31, 0.30), 0.94)
    water = material("River | glacial teal", (0.035, 0.29, 0.31), 0.22, 0.18)
    path = material("Trail | sunlit ochre", (0.43, 0.29, 0.16), 0.93)
    trunk = material("Tree | bark", (0.20, 0.12, 0.075), 0.96)
    leaves = [
        material("Canopy | evergreen", (0.075, 0.22, 0.15)),
        material("Canopy | jade", (0.11, 0.31, 0.20)),
        material("Canopy | sage", (0.24, 0.39, 0.24)),
    ]
    rocks = [
        material("Rock | shale", (0.31, 0.34, 0.34)),
        material("Rock | ochre granite", (0.43, 0.34, 0.25)),
        material("Rock | mossed slate", (0.20, 0.29, 0.25)),
    ]
    flowers = [
        material("Flower | pale gold", (0.96, 0.70, 0.28), 0.52, 0.0, 0.18),
        material("Flower | lilac", (0.56, 0.43, 0.78), 0.52, 0.0, 0.14),
        material("Flower | ivory", (0.91, 0.87, 0.72), 0.52, 0.0, 0.12),
    ]
    stem = material("Flower | stem", (0.10, 0.23, 0.12))
    rune = material("Ruin | sleeping rune", (0.10, 0.75, 0.66), 0.28, 0.16, 1.0)

    terrain = add_terrain(terrain_col, [grass, moss, stone], WORLD_SIZE, ARGS.grid)
    add_river(terrain_col, water, rocks[0])
    add_path(structure_col, path)
    add_environment(vegetation_col, (trunk, leaves, rocks, flowers, stem), ARGS.seed)
    add_ruin(structure_col, stone, rune)
    setup_lighting(light_col)
    setup_camera(light_col)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.fps = 30
    scene.view_settings.view_transform = "AgX"
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = ARGS.samples
    scene.render.filepath = str(output / "GAMEFORGE_Loomwild_1280x720.png")
    scene.frame_set(1)
    terrain["style"] = STYLE
    terrain["world_seed"] = ARGS.seed

    blend = output / "GAMEFORGE_Loomwild_Environment.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.render.render(write_still=True)

    glb = output / "GAMEFORGE_Loomwild_Environment.glb"
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = terrain
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", use_selection=False,
                              export_cameras=False, export_lights=False, export_materials="EXPORT")

    preview = output / "GAMEFORGE_Loomwild_1280x720.png"
    audit = {
        "project": "GAMEFORGE Loomwild procedural environment",
        "style": STYLE,
        "seed": ARGS.seed,
        "renderer": "Blender Eevee Next CPU",
        "preview_resolution": [WIDTH, HEIGHT],
        "terrain_grid": [ARGS.grid, ARGS.grid],
        "terrain_vertices": len(terrain.data.vertices),
        "terrain_faces": len(terrain.data.polygons),
        "counts": COUNTS,
        "outputs": {
            "blend": {"path": blend.name, "bytes": blend.stat().st_size},
            "glb": {"path": glb.name, "bytes": glb.stat().st_size},
            "preview": {"path": preview.name, "bytes": preview.stat().st_size},
        },
        "checks": {
            "terrain_mesh": len(terrain.data.vertices) >= 1000,
            "trees_generated": COUNTS["trees"] >= 40,
            "rocks_generated": COUNTS["rocks"] >= 60,
            "flowers_generated": COUNTS["flowers"] >= 20,
            "landmark_generated": COUNTS["landmarks"] >= 1,
            "river_and_trail": COUNTS["paths"] >= 1 and any(o.name.startswith("WORLD_RIVER") for o in bpy.data.objects),
            "blend_exported": blend.stat().st_size > 100000,
            "glb_exported": glb.stat().st_size > 100000,
            "preview_rendered": preview.stat().st_size > 20000,
        },
    }
    audit["failures"] = [key for key, passed in audit["checks"].items() if not passed]
    (output / "GAMEFORGE_Loomwild_Audit.json").write_text(json.dumps(audit, indent=2) + "\\n", encoding="utf-8")
    (output / "README.md").write_text(
        "# GAMEFORGE Loomwild environment build\\n\\n"
        "Deterministic painterly 3D landscape generated in Blender. Includes a sculpted heightfield, winding river, old trail, forest, rocks, wildflower patches and an ancient gateway. The .blend is editable, the GLB is the engine interchange asset and the 1280x720 PNG is the review render.\\n",
        encoding="utf-8"
    )
    if audit["failures"]:
        raise RuntimeError("World generation audit failed: " + ", ".join(audit["failures"]))
    print(json.dumps(audit, indent=2), flush=True)

if __name__ == "__main__":
    main()
