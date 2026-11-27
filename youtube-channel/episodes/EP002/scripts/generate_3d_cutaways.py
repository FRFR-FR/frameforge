#!/usr/bin/env python3
"""Ten animated Blender cutaways. These are conceptual reconstructions, not factory footage."""
import bpy, math, os, sys
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = os.path.abspath(args[args.index("--output-dir") + 1]) if "--output-dir" in args else os.path.abspath("output/3d_frames")
os.makedirs(out, exist_ok=True)
W, H, FPS, FRAMES = 1280, 720, 24, 288

def mat(n, c, metal=0.2, emit=None):
    m = bpy.data.materials.new(n)
    m.diffuse_color = (*c, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*c, 1)
    p.inputs["Metallic"].default_value = metal
    p.inputs["Roughness"].default_value = 0.25
    if emit:
        p.inputs["Emission Color"].default_value = (*emit, 1)
        p.inputs["Emission Strength"].default_value = 2.8
    return m

STEEL = mat("machined steel", (.19, .28, .39), .8)
DARK = mat("deep navy chamber", (.008, .02, .04), .5)
SILVER = mat("optical multilayer", (.65, .75, .86), .9)
WAFER = mat("silicon", (.06, .23, .42), .8)
GOLD = mat("reticle carrier", (.5, .32, .09), .7)
RED = mat("laser", (.9, .025, .04), .1, (1, .01, .02))
CYAN = mat("EUV path", (.02, .36, .9), .2, (.02, .28, 1))
HOT = mat("plasma", (1, .2, .015), .1, (1, .1, .005))
WHITE = mat("ceramic", (.85, .9, .96), .1)

def cube(n, loc, dim, material, bevel=.05):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = n
    o.dimensions = dim
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(material)
    if bevel:
        b = o.modifiers.new("edge bevel", "BEVEL")
        b.width = bevel
        b.segments = 3
    return o

def sphere(n, loc, r, material):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, radius=r, location=loc)
    o = bpy.context.object
    o.name = n
    o.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return o

def cyl(n, loc, r, depth, material):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=r, depth=depth, location=loc)
    o = bpy.context.object
    o.name = n
    o.data.materials.append(material)
    o.modifiers.new("edge bevel", "BEVEL").width = .03
    return o

def beam(n, a, b, r, material):
    a, b = Vector(a), Vector(b)
    v = b - a
    o = cyl(n, (a + b) / 2, r, v.length, material)
    o.rotation_euler = v.to_track_quat("Z", "Y").to_euler()
    return o

def animate(o, start, end):
    o.location = start
    o.keyframe_insert(data_path="location", frame=1)
    o.location = end
    o.keyframe_insert(data_path="location", frame=FRAMES)

def setup(folder, camloc=(8, -12, 7), target=(0, 0, 0)):
    scene = bpy.context.scene
    bpy.ops.object.camera_add(location=camloc)
    cam = bpy.context.object
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert(data_path="location", frame=1)
    cam.keyframe_insert(data_path="rotation_euler", frame=1)
    cam.location = Vector(camloc) * 0.93 + Vector(target) * 0.07
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert(data_path="location", frame=FRAMES)
    cam.keyframe_insert(data_path="rotation_euler", frame=FRAMES)
    scene.camera = cam
    world = bpy.data.worlds.new("studio world")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (.006, .014, .028, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .35
    for loc, power, size, col in [((2, -7, 9), 1700, 8, (.7, .82, 1)), ((-6, 2, 5), 1300, 6, (.18, .4, 1)), ((5, 5, 4), 900, 5, (1, .28, .12))]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.data.energy = power
        light.data.shape = "DISK"
        light.data.size = size
        light.data.color = col
        light.rotation_euler = (Vector((0, 0, 0)) - light.location).to_track_quat("-Z", "Y").to_euler()

    # GitHub-hosted runners do not expose a physical GPU. Eevee therefore
    # falls back to software OpenGL and makes a 2,880-frame animation take
    # impractically long. Workbench is still a true geometry-based 3D renderer;
    # studio lighting, material colours, shadows and cavity shading preserve
    # the technical explainer look while rendering much faster on CPU.
    supported = {item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items}
    if "BLENDER_WORKBENCH" not in supported:
        raise RuntimeError(f"Blender Workbench renderer is unavailable: {sorted(supported)}")
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "BOTH"
    shading.curvature_ridge_factor = 1.35
    shading.curvature_valley_factor = 1.1
    shading.show_specular_highlight = True
    shading.show_object_outline = True
    shading.object_outline_color = (0.008, 0.02, 0.04)
    shading.show_floor = False
    shading.show_axis_x = False
    shading.show_axis_y = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = max(1, min(8, os.cpu_count() or 2))
    scene.render.resolution_x = W
    scene.render.resolution_y = H
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = FRAMES
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = os.path.join(folder, "frame_")
    scene.view_settings.view_transform = "AgX"

def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

def scene_tin(folder):
    clear()
    cube("dark chamber", (0, 0, -.8), (10, 5, .3), DARK)
    for i in range(8):
        o = sphere("molten tin droplet", (-3.4 + i * .55, 0, .1), .15, HOT)
        animate(o, (-3.4 + i * .55, 0, .1), (-2.9 + i * .55, 0, .1))
    beam("focused laser beam", (-3, -2, 2), (0, 0, .2), .045, RED)
    p = sphere("plasma burst", (1, 0, .25), .24, HOT)
    p.scale = (.4, .4, .4)
    p.keyframe_insert(data_path="scale", frame=1)
    p.scale = (2.0, 1.5, 1.5)
    p.keyframe_insert(data_path="scale", frame=55)
    p.scale = (.8, .8, .8)
    p.keyframe_insert(data_path="scale", frame=FRAMES)
    setup(folder, (6, -9, 5), (0, 0, 0))

def scene_mirrors(folder):
    clear()
    cube("vacuum base", (0, 0, -.6), (11, 5, .4), DARK)
    for y in [-1.7, 1.7]:
        cube("open chamber rail", (0, y, .55), (9, .15, 2.4), STEEL)
    specs = [((-2.6, 0, .9), .42), ((0, 0, 1.35), -.5), ((2.6, 0, .9), .42)]
    for loc, ang in specs:
        mirror = cube("multilayer mirror", loc, (1.7, .17, 1.1), SILVER)
        mirror.rotation_euler[1] = ang
    pts = [(-4, 0, .1), (-2.6, 0, 1.15), (0, 0, .85), (2.6, 0, 1.15), (4, 0, .1)]
    for a, b in zip(pts, pts[1:]):
        beam("reflected EUV path", a, b, .035, CYAN)
    pulse = sphere("EUV pulse", pts[0], .14, CYAN)
    animate(pulse, pts[0], pts[-1])
    cyl("wafer", (4.25, 0, -.25), .9, .13, WAFER)
    setup(folder, (7, -11, 6), (0, 0, .5))

def scene_reticle(folder):
    clear()
    cube("base", (0, 0, -.65), (10, 6, .3), DARK)
    cube("reflective reticle", (-1.8, 0, 1.8), (2.5, 2, .12), GOLD)
    for i in range(-4, 5):
        cube("mask pattern", (-1.8 + i * .24, 0, 1.88), (.055, 1.5, .02), DARK, .005)
    for i in range(8):
        beam("projected beam", (-2.8 + i * .28, 0, 1.65), (.6 + i * .15, 0, .2), .012, CYAN)
    wafer = cyl("resist coated wafer", (1, 0, -.02), 1.6, .13, WAFER)
    animate(wafer, (1, 0, -.02), (.75, 0, -.02))
    for i in range(-4, 5):
        cube("exposed resist pattern", (1 + i * .24, 0, .055), (.045, 2.4, .02), WHITE, .003)
    setup(folder, (6, -10, 6), (0, 0, .55))

def scene_stage(folder):
    clear()
    cyl("precision stage base", (0, 0, -.1), 2.1, .5, STEEL)
    cyl("magnetic ring", (0, 0, .25), 1.75, .13, GOLD)
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x, y = 1.85 * math.cos(rad), 1.85 * math.sin(rad)
        cyl("precision actuator", (x, y, .6), .11, .65, STEEL)
        beam("metrology beam", (x * 1.1, y * 1.1, 1), (0, 0, 1.5), .015, CYAN)
    wafer = cyl("wafer on stage", (0, 0, 1.25), 1.7, .12, WAFER)
    animate(wafer, (-.12, 0, 1.25), (.12, 0, 1.25))
    setup(folder, (7, -10, 5.5), (0, 0, .5))

def scene_layers(folder):
    clear()
    cube("studio floor", (0, 0, -.6), (9, 7, .3), DARK)
    for i in range(6):
        z = .05 + i * .28
        disk = cyl("interconnected circuit layer", (0, 0, z), 1.8, .11, WAFER if i % 2 == 0 else STEEL)
        for j in range(-3, 4):
            trace = cube("interconnect trace", (j * .42, 0, z + .08), (.035, 2.8, .02), CYAN, .005)
            trace.rotation_euler[2] = i * .1
        animate(disk, (0, 0, z + 1), (0, 0, z))
    setup(folder, (7, -11, 6), (0, 0, .6))


def scene_wafer_macro(folder):
    clear()
    cube("cleanroom studio floor", (0, 0, -0.55), (9, 8, 0.3), DARK)
    wafer = cyl("full silicon wafer", (0, 0, 0), 2.25, 0.14, WAFER)
    for row in range(-4, 5):
        for column in range(-4, 5):
            x, y = column * 0.43, row * 0.43
            die = cube("repeating die field", (x, y, 0.095), (0.36, 0.36, 0.025), STEEL, 0.012)
            if (row + column) % 2 == 0:
                trace = cube("die interconnect", (x, y, 0.116), (0.26, 0.025, 0.012), CYAN, 0.002)
                trace.rotation_euler[2] = (row - column) * 0.07
    wafer.rotation_euler[2] = 0
    wafer.keyframe_insert(data_path="rotation_euler", frame=1)
    wafer.rotation_euler[2] = math.radians(18)
    wafer.keyframe_insert(data_path="rotation_euler", frame=FRAMES)
    setup(folder, (6, -9, 5), (0, 0, 0))


def scene_wavelength(folder):
    clear()
    cube("dark optics bench", (0, 0, -0.6), (10, 6, 0.3), DARK)
    for row, y, color, wavelength in [
        (0, -1.15, RED, 0.95),
        (1, 1.15, CYAN, 0.38)
    ]:
        points = []
        for index in range(65):
            x = -4.2 + index * 0.132
            z = 0.25 + math.sin(index * wavelength) * 0.28
            points.append((x, y, z))
        for a, b in zip(points, points[1:]):
            beam("conceptual wavelength path", a, b, 0.018, color)
        pulse = sphere("travelling light pulse", points[0], 0.12, color)
        animate(pulse, points[0], points[-1])
    setup(folder, (6, -10, 5.5), (0, 0, 0.2))


def scene_process_cycle(folder):
    clear()
    cube("process floor", (0, 0, -0.6), (11, 6, 0.3), DARK)
    stations = [
        (-3.6, "deposition chamber", STEEL),
        (-1.2, "lithography chamber", GOLD),
        (1.2, "etch chamber", STEEL),
        (3.6, "inspection chamber", SILVER)
    ]
    for x, name, material in stations:
        cube(name, (x, 0, 0.7), (1.5, 1.9, 1.8), material, 0.08)
        cube("process window", (x, -0.98, 0.8), (0.85, 0.05, 0.65), CYAN, 0.02)
        for side in (-1, 1):
            cyl("status lamp", (x + side * 0.52, -1.05, 1.35), 0.08, 0.08, RED)
    wafer = cyl("wafer moving between process tools", (-4.4, -0.2, -0.05), 0.55, 0.09, WAFER)
    animate(wafer, (-4.4, -0.2, -0.05), (4.4, -0.2, -0.05))
    setup(folder, (8, -13, 7), (0, 0, 0.4))


def scene_high_na(folder):
    clear()
    cube("optical comparison floor", (0, 0, -0.65), (10, 6, 0.3), DARK)
    for x, aperture, color in [(-2.2, 0.72, RED), (2.2, 1.15, CYAN)]:
        cyl("optical aperture", (x, 0, 0.75), aperture, 0.18, STEEL)
        for angle in range(0, 360, 30):
            rad = math.radians(angle)
            start = (x + aperture * math.cos(rad), aperture * math.sin(rad), 0.85)
            end = (x * 0.15, 0.0, -0.05)
            beam("numerical aperture ray", start, end, 0.018, color)
        wafer = cyl("exposure plane", (x * 0.15, 0, -0.18), 0.8, 0.1, WAFER)
        wafer.scale = (0.9, 0.9, 0.9)
    setup(folder, (7, -12, 6), (0, 0, 0.25))


def scene_supply_chain(folder):
    clear()
    cube("factory floor", (0, 0, -0.65), (10, 8, 0.3), DARK)
    wafer = cyl("central silicon wafer", (0, 0, 0), 1.35, 0.12, WAFER)
    for angle in range(0, 360, 60):
        rad = math.radians(angle)
        x, y = 3.1 * math.cos(rad), 3.1 * math.sin(rad)
        cube("supporting process tool", (x, y, 0.55), (1.2, 1.2, 1.4), STEEL, 0.08)
        cube("tool inspection window", (x, y - 0.62, 0.65), (0.55, 0.05, 0.5), CYAN, 0.02)
        beam("factory material route", (x * 0.78, y * 0.78, 0.45), (0, 0, 0.2), 0.025, CYAN)
        arm = cyl("robotic transfer arm", (x * 0.6, y * 0.6, 0.95), 0.09, 1.0, GOLD)
        arm.rotation_euler[2] = rad
        arm.keyframe_insert(data_path="rotation_euler", frame=1)
        arm.rotation_euler[2] = rad + math.radians(35)
        arm.keyframe_insert(data_path="rotation_euler", frame=FRAMES)
    wafer.rotation_euler[2] = 0
    wafer.keyframe_insert(data_path="rotation_euler", frame=1)
    wafer.rotation_euler[2] = math.radians(24)
    wafer.keyframe_insert(data_path="rotation_euler", frame=FRAMES)
    setup(folder, (8, -12, 7), (0, 0, 0.25))


SCENES = [
    ("scene_01_wafer_macro", scene_wafer_macro),
    ("scene_02_layer_stack", scene_layers),
    ("scene_03_wavelength", scene_wavelength),
    ("scene_04_tin_plasma", scene_tin),
    ("scene_05_mirror_optics", scene_mirrors),
    ("scene_06_reticle_projection", scene_reticle),
    ("scene_07_wafer_stage", scene_stage),
    ("scene_08_process_cycle", scene_process_cycle),
    ("scene_09_high_na", scene_high_na),
    ("scene_10_supply_chain", scene_supply_chain)
]
def make_progress_handler(name):
    def report_frame(scene, *args):
        frame = scene.frame_current
        if frame == 1 or frame % 48 == 0 or frame == FRAMES:
            print(f"FRAME_PROGRESS {name} {frame}/{FRAMES}", flush=True)
    return report_frame


for name, function in SCENES:
    folder = os.path.join(out, name)
    os.makedirs(folder, exist_ok=True)
    function(folder)
    handler = make_progress_handler(name)
    bpy.app.handlers.render_write.append(handler)
    print(f"STARTING_RENDER {name} engine={bpy.context.scene.render.engine} size={W}x{H} fps={FPS} frames={FRAMES}", flush=True)
    bpy.ops.render.render(animation=True)
    bpy.app.handlers.render_write.remove(handler)
    print("RENDERED", name, flush=True)
