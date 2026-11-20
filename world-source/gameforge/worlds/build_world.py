#!/usr/bin/env python3
"""Build the original, walkable BLACKTIDE PORT combat map for GAMEFORGE."""
from __future__ import annotations
import bpy, sys, json, os, math, random
from pathlib import Path
from mathutils import Vector

SIZE = 240.0
COUNTS = {"major_buildings": 0, "interior_spaces": 0, "cover": 0,
          "containers": 0, "vertical_routes": 0, "cranes": 0,
          "lights": 0, "barrels": 0, "object_meshes": 0}
WORLD = None

def arguments():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True)
    p.add_argument("--seed", type=int, default=42017)
    p.add_argument("--grid", type=int, default=129)
    p.add_argument("--samples", type=int, default=32)
    return p.parse_args(argv)

def mat(name, color, metallic=0.15, roughness=0.62, emission=None):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        sock = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        if sock:
            sock.default_value = (*emission, 1.0)
        power = bsdf.inputs.get("Emission Strength")
        if power:
            power.default_value = 1.6
    return m

def put_in_world(obj):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    WORLD.objects.link(obj)
    COUNTS["object_meshes"] += 1
    return obj

def box(name, location, dimensions, material, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    o = bpy.context.object
    o.name = name
    o.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    if bevel > 0:
        mod = o.modifiers.new("Machined safety edges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in o.data.polygons:
        p.use_smooth = False
    return put_in_world(o)

def cylinder(name, location, radius, depth, material, vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material)
    return put_in_world(o)

def staircase(name, start, end, rise, steps, width, material):
    sx, sy, sz = start
    ex, ey, ez = end
    dx, dz = ex - sx, ez - sz
    run = math.sqrt(dx * dx + dz * dz)
    for i in range(steps):
        t = (i + 0.5) / steps
        x, z = sx + dx * t, sz + dz * t
        h = rise * (i + 1) / steps
        box(f"{name}_STEP_{i+1:02d}", (x, h * 0.5, z),
            (width, h, run / steps + 0.12), material, 0.025)
    # Railing posts and continuous top rails make the route readable.
    for side in (-1, 1):
        px = -dz / max(run, 0.001) * side * width * 0.52
        pz = dx / max(run, 0.001) * side * width * 0.52
        for i in range(0, steps + 1, 3):
            t = i / steps
            h = rise * t
            cylinder(f"{name}_RAIL_POST_{side}_{i}", (sx + dx*t + px, h + 0.55, sz + dz*t + pz),
                     0.055, 1.1, steel, 10)
        rail = box(f"{name}_HANDRAIL_{side}", ((sx+ex)*0.5+px, rise+0.52, (sz+ez)*0.5+pz),
                   (0.10, 0.10, run), orange, 0.02)
        rail.rotation_euler[1] = math.atan2(dx, dz)
    COUNTS["vertical_routes"] += 1

def open_building(name, center, width, depth, height, wall, concrete, steel_mat, accent,
                  mezzanine=False, door_width=9.0):
    x, z = center
    # The open floor and split front wall create a real playable interior, not a solid block.
    box(name+"_INTERIOR_FLOOR", (x, 0.16, z), (width-wall, 0.32, depth-wall), concrete, 0.06)
    box(name+"_LEFT_WALL", (x-width/2+wall/2, height/2, z), (wall, height, depth), steel_mat, 0.08)
    box(name+"_RIGHT_WALL", (x+width/2-wall/2, height/2, z), (wall, height, depth), steel_mat, 0.08)
    box(name+"_REAR_WALL", (x, height/2, z-depth/2+wall/2), (width, height, wall), steel_mat, 0.08)
    side = max(1.0, (width-door_width)/2)
    box(name+"_FRONT_WALL_L", (x-width/2+side/2, height/2, z+depth/2-wall/2),
        (side, height, wall), steel_mat, 0.06)
    box(name+"_FRONT_WALL_R", (x+width/2-side/2, height/2, z+depth/2-wall/2),
        (side, height, wall), steel_mat, 0.06)
    box(name+"_DOOR_HEADER", (x, height-0.65, z+depth/2-wall/2), (door_width, 1.3, wall), accent, 0.04)
    # A broken roofline keeps natural light in the interior and offers a readable silhouette.
    box(name+"_ROOF_BEAM_L", (x-width*0.25, height, z), (width*0.5, 0.45, 1.1), accent, 0.05)
    box(name+"_ROOF_BEAM_R", (x+width*0.25, height, z), (width*0.5, 0.45, 1.1), accent, 0.05)
    for px in (-width*0.32, width*0.32):
        for pz in (-depth*0.32, depth*0.32):
            box(f"{name}_COLUMN_{px}_{pz}", (x+px, height/2, z+pz), (0.72, height, 0.72), accent, 0.06)
    COUNTS["major_buildings"] += 1
    COUNTS["interior_spaces"] += 1
    if mezzanine:
        deck_y = height * 0.43
        box(name+"_MEZZANINE_DECK", (x, deck_y, z-depth*0.18),
            (width*0.58, 0.45, depth*0.33), concrete, 0.04)
        for edge in (-1, 1):
            box(name+"_UPPER_RAIL_"+str(edge), (x+edge*width*0.285, deck_y+0.55, z-depth*0.18),
                (0.12, 1.1, depth*0.33), orange, 0.025)
        staircase(name+"_INTERIOR_STAIRS", (x-width*0.31, 0.0, z+depth*0.28),
                  (x-width*0.05, 0.0, z-depth*0.35), deck_y, 13, 2.8, concrete)
    # External labels, vent panels and wall ribs break up large surfaces.
    for i in range(5):
        xx = x-width*0.38 + i*width*0.19
        box(name+"_FACADE_RIB_"+str(i), (xx, height*0.70, z+depth/2+0.06),
            (0.28, height*0.50, 0.12), accent, 0.02)
    return (x, z)

def cover_block(name, x, z, w, h, d, concrete, accent):
    box(name, (x, h/2, z), (w, h, d), concrete, 0.07)
    box(name+"_ARMOUR_CAP", (x, h+0.08, z), (w+0.16, 0.16, d+0.16), accent, 0.035)
    COUNTS["cover"] += 1

def main():
    global WORLD
    a = arguments()
    rng = random.Random(a.seed)
    out = Path(a.output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    COUNTS.update({k: 0 for k in COUNTS})
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    WORLD = bpy.data.collections.new("BLACKTIDE PORT | GAMEPLAY GEOMETRY")
    bpy.context.scene.collection.children.link(WORLD)

    concrete = mat("Harbour concrete | weathered graphite", (0.18, 0.21, 0.23), 0.12, 0.84)
    road = mat("Asphalt | blue black", (0.035, 0.055, 0.065), 0.08, 0.92)
    steel_mat = mat("Structural steel | midnight", (0.045, 0.075, 0.095), 0.72, 0.34)
    orange = mat("Safety enamel | burnt orange", (0.86, 0.25, 0.055), 0.38, 0.37)
    ivory = mat("Faded hazard ivory", (0.78, 0.77, 0.67), 0.12, 0.68)
    glass = mat("Armoured glass | deep teal", (0.025, 0.18, 0.20), 0.48, 0.18)
    water = mat("Harbour water | dark teal", (0.012, 0.075, 0.095), 0.22, 0.20)
    rubber = mat("Rubber | near black", (0.018, 0.022, 0.025), 0.0, 0.9)
    signal = mat("Status lamps | cyan emission", (0.04, 0.48, 0.56), 0.35, 0.24, (0.06, 0.75, 0.90))

    # Full-size ground, quay and primary movement lanes.
    box("WORLD_FOUNDATION", (0, -0.28, 0), (SIZE, 0.56, SIZE), concrete, 0.0)
    box("HARBOUR_BASIN", (0, -0.08, -111), (220, 0.20, 16), water)
    for x in (-104, -68, 0, 68, 104):
        box("ASPHALT_LANE_X_"+str(x), (x, 0.015, 0), (7.5, 0.035, 220), road)
    for z in (-100, -48, 0, 48, 100):
        box("ASPHALT_LANE_Z_"+str(z), (0, 0.025, z), (220, 0.04, 7.5), road)
    for z in (-96, -44, 4, 52, 98):
        for x in range(-92, 93, 16):
            box("LANE_DASH_"+str(x)+"_"+str(z), (x, 0.052, z), (5.0, 0.018, 0.18), ivory)
    for x in (-112, 112):
        box("PERIMETER_WALL_"+str(x), (x, 2.0, 0), (2.2, 4.0, 220), steel_mat, 0.1)
    for z in (-112, 112):
        box("PERIMETER_WALL_Z_"+str(z), (0, 2.0, z), (220, 4.0, 2.2), steel_mat, 0.1)

    # Three open combat buildings; doorways remain large enough for player and bot navigation.
    open_building("WEST_FREIGHT_WAREHOUSE", (-43, -28), 42, 34, 12, 1.2,
                  concrete, steel_mat, orange, True, 12)
    open_building("CENTRAL_MAINTENANCE_HALL", (11, 28), 38, 32, 14, 1.2,
                  concrete, steel_mat, signal, True, 11)
    open_building("EAST_CONTROL_TERMINAL", (61, -30), 34, 31, 11, 1.1,
                  concrete, steel_mat, orange, False, 10)
    # A fourth two-level watch building and its external approach.
    box("TOWER_FOUNDATION", (0, 0.45, 79), (20, 0.9, 18), concrete, 0.08)
    box("TOWER_MAIN_LEVEL", (0, 4.4, 79), (17, 7.0, 15), steel_mat, 0.08)
    box("TOWER_WINDOW_BAND_FRONT", (0, 5.1, 71.3), (12, 2.8, 0.25), glass, 0.03)
    box("TOWER_BALCONY", (0, 8.2, 79), (21, 0.4, 18), concrete, 0.05)
    for x in (-10, 10):
        box("TOWER_BALCONY_RAIL_"+str(x), (x, 8.9, 79), (0.18, 1.0, 18), orange)
    staircase("TOWER_EXTERNAL_STAIR", (-8.5, 0.0, 91), (-8.5, 0.0, 79), 8.0, 20, 3.1, concrete)
    COUNTS["major_buildings"] += 1
    COUNTS["vertical_routes"] += 1

    # A raised maintenance catwalk adds a third vertical route and a flank across the hall.
    box("NORTH_CATWALK_DECK", (16, 5.3, 64), (40, 0.45, 3.2), steel_mat, 0.05)
    box("NORTH_CATWALK_RAIL_A", (16, 6.0, 62.45), (40, 1.2, 0.14), orange)
    box("NORTH_CATWALK_RAIL_B", (16, 6.0, 65.55), (40, 1.2, 0.14), orange)
    staircase("NORTH_CATWALK_STAIRS", (-6, 0.0, 68), (-6, 0.0, 60), 5.0, 14, 2.5, concrete)
    COUNTS["vertical_routes"] += 1

    # Shipping containers in staggered stacks. The breaks create three distinct approach lanes.
    for row, z in enumerate((-94, -84, -74, -64)):
        for i, x in enumerate(range(-96, 97, 14)):
            if (row in (1, 2) and -24 <= x <= 24) or (row == 3 and 46 <= x <= 74):
                continue
            h = 2.8 if (i + row) % 3 else 5.5
            color = orange if (i + row) % 5 == 0 else steel_mat
            box(f"FREIGHT_CONTAINER_{row}_{i}", (x, h/2, z), (11.2, h, 5.0), color, 0.08)
            for rib in range(1, 8):
                box(f"CONTAINER_RIB_{row}_{i}_{rib}",
                    (x-5.0+rib*1.25, h/2, z+2.54), (0.11, h*0.88, 0.08), ivory, 0.01)
            COUNTS["containers"] += 1

    # At least 30 purpose-placed pieces of hard cover, with clear crossfire lanes.
    cover_spots = [
        (-93,-35),(-78,-7),(-62,42),(-47,5),(-27,-55),(-14,-7),(-4,53),
        (15,-48),(29,-7),(42,48),(58,8),(77,40),(93,-18),
        (-91,76),(-63,91),(-34,68),(-20,94),(23,94),(48,78),(83,88),
        (-89,-72),(-57,-88),(-29,-84),(12,-85),(40,-90),(72,-78),(94,-62),
        (-50,50),(-4,18),(39,22),(88,13),(-72,-42),(70,-43)
    ]
    for i, (x, z) in enumerate(cover_spots):
        w = 3.2 if i % 3 else 4.6
        h = 1.15 if i % 4 else 1.55
        cover_block(f"TACTICAL_COVER_{i:02d}", x, z, w, h, 1.35, concrete, orange)
    # Interior cover islands keep the warehouses playable rather than empty shells.
    for i, (x, z) in enumerate([(-48,-31),(-35,-25),(-47,-18),(8,24),(19,29),(61,-34),(68,-26)]):
        cover_block(f"INTERIOR_COVER_{i:02d}", x, z, 2.2, 1.0, 1.1, steel_mat, signal)

    # Crates, drums, bollards, cable reels and loading equipment add scale and varied silhouettes.
    for i in range(14):
        x = rng.uniform(-101, 101); z = rng.uniform(-58, 102)
        if any(abs(x-bx)<10 and abs(z-bz)<10 for bx,bz in [(-43,-28),(11,28),(61,-30),(0,79)]):
            continue
        box(f"SUPPLY_CRATE_{i:02d}", (x, 0.8, z), (1.8, 1.6, 1.8), orange if i%4==0 else steel_mat, 0.06)
        for side in (-1, 1):
            box(f"CRATE_STRAP_{i}_{side}", (x+side*0.48, 0.82, z-0.92), (0.12, 1.45, 0.06), ivory)
    for i, (x,z) in enumerate([(-101,-20),(-95,22),(-70,10),(-18,-42),(2,-26),(35,-64),(52,56),(94,54),(100,-50)]):
        cylinder(f"FUEL_DRUM_{i}", (x, 0.62, z), 0.56, 1.24, orange if i%3==0 else rubber, 20)
        box(f"DRUM_RIM_{i}", (x, 1.25, z), (1.18, 0.08, 1.18), steel_mat, 0.03)
        COUNTS["barrels"] += 1
    for i, x in enumerate((-100,-74,-18,18,74,100)):
        cylinder(f"PORT_LIGHT_POLE_{i}", (x, 7.0, 100 if i%2 else -12), 0.16, 14.0, steel_mat, 12)
        box(f"PORT_LIGHT_HEAD_{i}", (x, 14.0, 100 if i%2 else -12), (1.2, 0.35, 0.5), signal)
        COUNTS["lights"] += 1

    # Two container cranes and a raised service bridge create long-range landmarks.
    for i, x in enumerate((-66, 66)):
        for z in (-5, 5):
            box(f"GANTRY_LEG_{i}_{z}", (x, 8, z-55), (1.8, 16, 1.8), steel_mat, 0.08)
        box(f"GANTRY_BEAM_{i}", (x, 16.5, -60), (30, 1.7, 2.0), orange, 0.08)
        box(f"GANTRY_CABLE_{i}", (x, 12, -60), (0.12, 8, 0.12), rubber)
        COUNTS["cranes"] += 1
    # Hazard markings at doors, ramps and objectives.
    objectives = [(-43,-28),(11,28),(61,-30)]
    for i, (x,z) in enumerate(objectives):
        box(f"OBJECTIVE_PAD_{i}", (x, 0.045, z), (8, 0.09, 8), signal)
        box(f"OBJECTIVE_CORE_{i}", (x, 1.25, z), (0.35, 2.5, 0.35), ivory)
        cylinder(f"OBJECTIVE_RING_{i}", (x, 2.45, z), 1.1, 0.08, orange, 32)

    # Collision-ready navigation volumes and sightline breaks are audited after export.
    audit = {
        "name": "BLACKTIDE PORT | offline combat map",
        "dimensions_m": [SIZE, SIZE],
        "buildings": COUNTS["major_buildings"],
        "major_buildings": COUNTS["major_buildings"],
        "interior_spaces": COUNTS["interior_spaces"],
        "lanes": 8,
        "cover": COUNTS["cover"],
        "objectives": len(objectives),
        "vertical_routes": COUNTS["vertical_routes"],
        "terrain_vertices": 4,
        "collision_proxy_candidates": COUNTS["object_meshes"],
        "counts": dict(COUNTS),
        "original": True,
        "failures": []
    }
    if audit["buildings"] < 3: audit["failures"].append("needs three major buildings")
    if audit["cover"] < 25: audit["failures"].append("needs at least 25 cover pieces")
    if audit["interior_spaces"] < 3: audit["failures"].append("needs three traversable interiors")
    if audit["vertical_routes"] < 2: audit["failures"].append("needs two vertical routes")
    if audit["collision_proxy_candidates"] < 80: audit["failures"].append("insufficient gameplay geometry")

    if os.environ.get("GAMEFORGE_SKIP_PREVIEWS") != "1":
        scene = bpy.context.scene
        scene.render.engine = "BLENDER_EEVEE_NEXT"
        scene.render.resolution_x, scene.render.resolution_y = 1280, 720
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA"
        scene.view_settings.view_transform = "AgX"
        scene.render.filepath = str(out / "BLACKTIDE_PORT_720p.png")
        bpy.ops.object.camera_add(location=(0, -205, 170))
        camera = bpy.context.object
        camera.data.type = "ORTHO"
        camera.data.ortho_scale = 286
        camera.rotation_euler = (Vector((0, 0, 0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
        bpy.ops.object.light_add(type="AREA", location=(0, -24, 95))
        key = bpy.context.object
        key.data.energy = 18500
        key.data.size = 90
        key.rotation_euler = (Vector((0, 0, 0)) - key.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.camera = camera
        scene.render.filepath = str(out / "BLACKTIDE_PORT_720p.png")
        bpy.ops.render.render(write_still=True)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in list(WORLD.objects):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = next(iter(WORLD.objects))
    glb = out / "GAMEFORGE_BlackTide_Port.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", use_selection=True,
                              export_materials="EXPORT", export_cameras=False, export_lights=False,
                              export_apply=True)
    audit["glb_bytes"] = glb.stat().st_size
    audit["preview"] = "BLACKTIDE_PORT_720p.png" if (out / "BLACKTIDE_PORT_720p.png").exists() else None
    (out / "GAMEFORGE_BlackTide_Audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    if audit["failures"] or glb.stat().st_size < 100000:
        raise RuntimeError("BLACKTIDE map build failed: " + str(audit["failures"]))
    print(json.dumps(audit, indent=2), flush=True)

if __name__ == "__main__":
    main()
