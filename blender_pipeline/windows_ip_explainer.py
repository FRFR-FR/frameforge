#!/usr/bin/env python3
"""FrameForge: 90-second Windows IP privacy explainer.

Stylised 3D educational animation for Blender. Ten visual chapters, six
renderable 15-second sections, vertical 720x1280 at 30 FPS.
"""
import bpy
import math
import os
import sys
import json
import argparse
import subprocess
from mathutils import Vector

FPS = 30
DURATION = 90
WIDTH, HEIGHT = 720, 1280
TOTAL_FRAMES = FPS * DURATION
SEGMENT_FRAMES = 15 * FPS
SHOT_FRAMES = 9 * FPS
OUT_NAME = "FrameForge_Windows_IP_Privacy_90s"

C = {
    "sky": (0.48, 0.72, 0.84, 1), "grass": (0.25, 0.52, 0.30, 1),
    "grass2": (0.48, 0.69, 0.36, 1), "cream": (0.96, 0.91, 0.78, 1),
    "white": (0.99, 0.98, 0.92, 1), "blue": (0.045, 0.14, 0.34, 1),
    "blue2": (0.05, 0.34, 0.68, 1), "cyan": (0.08, 0.69, 0.76, 1),
    "teal": (0.06, 0.49, 0.43, 1), "green": (0.22, 0.58, 0.31, 1),
    "lime": (0.70, 0.84, 0.40, 1), "red": (0.83, 0.23, 0.19, 1),
    "orange": (0.96, 0.53, 0.19, 1), "ink": (0.035, 0.075, 0.12, 1),
    "muted": (0.30, 0.39, 0.43, 1), "lavender": (0.47, 0.48, 0.72, 1),
    "glass": (0.66, 0.84, 0.89, 1), "silver": (0.52, 0.61, 0.64, 1),
}

SHOTS = [
    ("YOUR IP IS YOUR INTERNET ADDRESS", "A public return address for your connection"),
    ("IT CAN REVEAL YOUR APPROXIMATE REGION", "It is not your exact home address"),
    ("WINDOWS VPN SETTINGS ARE NOT A VPN SERVICE", "A VPN profile still needs a provider and server"),
    ("MEET EDGE SECURE NETWORK", "A VPN-style privacy feature built into Microsoft Edge"),
    ("OPEN SECURE NETWORK", "Three dots  >  More tools  >  Secure Network"),
    ("SIGN IN AND ENABLE PROTECTION", "Use a personal Microsoft account"),
    ("CHOOSE YOUR PROTECTION MODE", "Optimized  |  Select Sites  |  All Sites"),
    ("CHECK FOR THE SHIELD", "The shield appears when Secure Network is active"),
    ("COMPARE YOUR PUBLIC IP", "Check before and after on a trusted IP-check site"),
    ("KNOW THE LIMITS", "5 GB per month  |  Edge browsing  |  Not anonymity"),
]

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("audit", "render"), default="audit")
    p.add_argument("--segment-index", type=int, default=0)
    p.add_argument("--output-dir", default="output/windows_ip_explainer")
    return p.parse_args(argv)

def material(name, color, metallic=0.0, roughness=0.58, emission=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = color
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    if bs:
        bs.inputs["Base Color"].default_value = color
        bs.inputs["Metallic"].default_value = metallic
        bs.inputs["Roughness"].default_value = roughness
        if emission:
            bs.inputs["Emission Color"].default_value = color
            bs.inputs["Emission Strength"].default_value = emission
    return m

def cube(name, loc, scale, mat, bevel=0.0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.rotation_euler = rot
    if mat:
        o.data.materials.append(mat)
    if bevel:
        mod = o.modifiers.new("Soft bevel highlights", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        o.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return o

def ico(name, loc, scale, mat, subdivisions=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    if mat:
        o.data.materials.append(mat)
    return o

def cylinder(name, loc, radius, depth, mat, rot=(0, 0, 0), vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    if mat:
        o.data.materials.append(mat)
    mod = o.modifiers.new("Edge bevel", "BEVEL")
    mod.width = min(radius * 0.12, 0.06)
    mod.segments = 2
    o.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return o

def torus(name, loc, major, minor, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
        major_segments=48, minor_segments=10, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    if mat:
        o.data.materials.append(mat)
    return o

def text3d(name, body, loc, size, mat, align="CENTER"):
    d = bpy.data.curves.new(name, "FONT")
    d.body = body
    d.size = size
    d.align_x = align
    d.align_y = "CENTER"
    d.extrude = 0.004
    d.bevel_depth = 0.0015
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (math.pi / 2, 0, 0)
    if mat:
        d.materials.append(mat)
    return o

def line(name, points, thickness, mat):
    d = bpy.data.curves.new(name, "CURVE")
    d.dimensions = "3D"
    d.bevel_depth = thickness
    d.bevel_resolution = 3
    spline = d.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (co[0], co[1], co[2], 1)
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    if mat:
        d.materials.append(mat)
    return o

def label_card(name, x, y, z, width, height, title, subtitle, mats, accent="cyan"):
    card = cube(name + " panel", (x, y, z), (width, 0.32, height), mats["white"], 0.16)
    cube(name + " accent", (x - width/2 + 0.12, y - 0.18, z), (0.13, 0.05, height-0.38), mats[accent], 0.04)
    text3d(name + " title", title, (x, y-0.20, z+0.28), 0.34, mats["blue"])
    text3d(name + " subtitle", subtitle, (x, y-0.21, z-0.36), 0.19, mats["muted"])
    return card

def animate_float(obj, start, end, amplitude=0.25, turns=0.5):
    base = obj.location.copy()
    rot = obj.rotation_euler.copy()
    for frame, offset in ((start, -amplitude), ((start+end)//2, amplitude), (end, -amplitude)):
        obj.location = (base.x, base.y, base.z + offset)
        obj.rotation_euler = (rot.x, rot.y, rot.z + turns * 2*math.pi * (frame-start)/(end-start))
        obj.keyframe_insert(data_path="location", frame=frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)

def make_globe(x, mats, z=4.15):
    globe = ico("Faceted blue globe", (x, 0.6, z), (2.25, 2.25, 2.25), mats["blue2"], 3)
    for i, (dx, dz, sx, sz) in enumerate([
        (-0.85, 0.68, 0.68, 0.55), (0.35, 0.82, 0.57, 0.76),
        (0.77, -0.35, 0.78, 0.42), (-0.55, -0.78, 0.48, 0.69)
    ]):
        yy = 0.6 - math.sqrt(max(0.2, 2.25**2-dx**2-dz**2))*0.96
        ico("Raised green continent %d" % i, (x+dx, yy, z+dz), (sx, 0.08, sz), mats["lime"], 1)
    ring = torus("Orbiting network ring", (x, 0.6, z), 2.75, 0.045, mats["cyan"], (math.radians(70), 0, math.radians(25)))
    animate_float(globe, 1, TOTAL_FRAMES, 0.10, 0.16)
    animate_float(ring, 1, TOTAL_FRAMES, 0.05, 0.7)
    return globe

def stage(index, mats, camera):
    x = index * 28.0
    cube("Stage %02d meadow" % index, (x, 1.0, -0.62), (18, 24, 0.75), mats["grass"], 0.22)
    cube("Stage %02d cream podium" % index, (x, 0.0, -0.17), (12.8, 12.5, 0.18), mats["cream"], 0.16)
    for j, (dx, yy, sx, sy, sz) in enumerate([
        (-7, 8, 3.4, 2.1, 1.9), (-2.3, 10, 4.2, 2.2, 2.0),
        (3.6, 9.2, 4.3, 2.3, 1.8), (7.4, 11, 3.0, 1.8, 1.6)
    ]):
        ico("Stage %02d distant hill %d" % (index, j), (x+dx, yy, 0.1), (sx, sy, sz), mats["grass2"], 2)
    head, sub = SHOTS[index]
    h = text3d("Chapter %02d title" % index, head, (x, -6.7, 10.2), 0.64, mats["blue"])
    s = text3d("Chapter %02d descriptor" % index, sub, (x, -6.72, 9.20), 0.26, mats["muted"])
    h.scale = (0.94, 0.94, 0.94)
    h.keyframe_insert(data_path="scale", frame=index*SHOT_FRAMES+1)
    h.scale = (1.0, 1.0, 1.0)
    h.keyframe_insert(data_path="scale", frame=index*SHOT_FRAMES+13)
    # The chapter camera is driven to the matching stage at each 9-second cut.
    return x

def build_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    mats = {k: material(k, v, 0.05 if k in ("blue", "blue2", "cyan", "silver") else 0.0)
            for k, v in C.items()}
    # World and lighting: soft studio key, cool fill, warm rim.
    world = bpy.data.worlds.new("FrameForge sky") if not bpy.data.worlds else bpy.data.worlds[0]
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = C["sky"]
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55
    for name, loc, power, size, color in [
        ("Large soft key", (0, -10, 17), 1700, 10, (1.0, 0.88, 0.70)),
        ("Cool fill", (10, -3, 10), 1050, 8, (0.48, 0.75, 1.0)),
        ("Warm rim", (-8, 8, 12), 1300, 7, (1.0, 0.62, 0.35))
    ]:
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.name = name
        light.data.energy = power
        light.data.shape = "DISK"
        light.data.size = size
        light.data.color = color
        light.rotation_euler = (math.radians(24), 0, math.radians(20))
    bpy.ops.object.camera_add(location=(0, -24.5, 12.6))
    camera = bpy.context.object
    camera.name = "Vertical chapter camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 17.2
    bpy.context.scene.camera = camera
    # Common decorative network nodes, animated as a subtle orbit in each stage.
    for i in range(10):
        x = stage(i, mats, camera)
        start = i * SHOT_FRAMES + 1
        end = min((i+1)*SHOT_FRAMES, TOTAL_FRAMES)
        accent = mats["cyan"] if i % 2 == 0 else mats["orange"]
        for j in range(5):
            a = 2*math.pi*j/5
            node = ico("Floating network mote", (x+5.5*math.cos(a), 1.0+3.4*math.sin(a), 4.1+0.55*(j%2)), (0.12,0.12,0.12), accent, 1)
            animate_float(node, start, end, 0.20, 0.30)

        if i == 0:
            make_globe(x, mats, 4.1)
            cube("IP return address plaque", (x-4.0, -0.3, 3.7), (3.1, 0.25, 1.7), mats["white"], 0.16)
            text3d("IP plaque heading", "PUBLIC IP", (x-4.0, -0.48, 4.05), 0.27, mats["blue"])
            text3d("IP plaque number", "203.0.113.42", (x-4.0, -0.49, 3.55), 0.23, mats["teal"])
            line("Connection route", [(x-2.3,0,3.8),(x-1.2,-0.1,4.0),(x-0.5,0,4.2)], 0.05, mats["orange"])
        elif i == 1:
            g = make_globe(x, mats, 4.0)
            torus("Region locator target", (x+0.65,-1.25,4.8), 0.78, 0.06, mats["orange"], (math.pi/2,0,0))
            cylinder("Location pin stem", (x+0.65,-1.5,5.35), 0.16, 0.75, mats["red"])
            ico("Location pin head", (x+0.65,-1.5,5.83), (0.34,0.22,0.34), mats["red"], 2)
            label_card("Approximate region", x-4.0, -0.8, 3.4, 3.3, 1.55, "REGION", "Not a street address", mats, "orange")
        elif i == 2:
            label_card("Windows VPN settings", x, 0.0, 4.3, 7.4, 4.8, "WINDOWS VPN", "Create a connection profile", mats, "blue2")
            for k, txt in enumerate(["Provider: Windows (built-in)", "Server name or address: required", "Sign-in details: provider supplied"]):
                text3d("VPN profile row", txt, (x, -0.22, 5.05-k*0.72), 0.23, mats["ink"], "CENTER")
            cube("Needs external service tag", (x, -0.27, 2.3), (4.9, 0.42, 0.65), mats["orange"], 0.12)
            text3d("VPN server warning", "NEEDS A VPN SERVER", (x, -0.51, 2.3), 0.22, mats["ink"])
        elif i == 3:
            label_card("Edge Secure Network", x, 0.0, 4.1, 8.0, 4.5, "MICROSOFT EDGE", "Secure Network is built into the browser", mats, "cyan")
            torus("Secure Network symbol", (x, -0.45, 4.1), 1.0, 0.20, mats["teal"], (math.pi/2,0,0))
            ico("Secure Network inner core", (x, -0.62, 4.1), (0.42,0.18,0.42), mats["lime"], 2)
            text3d("Secure Network badge", "SECURE NETWORK", (x, -0.55, 2.65), 0.28, mats["blue"])
        elif i == 4:
            label_card("Edge menu tutorial", x, 0.3, 4.15, 6.6, 4.9, "EDGE MENU", "Open the browser menu", mats, "blue2")
            for k, txt in enumerate(["Settings", "More tools", "Secure Network  >"]):
                z = 5.05-k*0.92
                cube("Menu row %d" % k, (x, -0.34, z), (5.3,0.12,0.62), mats["glass"] if k==2 else mats["cream"], 0.08)
                text3d("Menu item %d" % k, txt, (x, -0.47, z), 0.30, mats["blue"])
            torus("Menu cursor ring", (x+2.45,-0.55,3.21), 0.27, 0.055, mats["orange"], (math.pi/2,0,0))
        elif i == 5:
            label_card("Account activation", x, 0.2, 4.2, 7.5, 4.3, "PERSONAL ACCOUNT", "Sign in to enable Secure Network", mats, "cyan")
            ico("Account avatar", (x-2.25,-0.55,4.2), (0.66,0.32,0.66), mats["blue2"], 2)
            cube("VPN toggle track", (x+1.2,-0.5,3.55), (2.0,0.18,0.72), mats["green"], 0.34)
            knob = ico("VPN toggle knob", (x+1.8,-0.68,3.55), (0.42,0.22,0.42), mats["white"], 2)
            knob.location.x = x+0.55
            knob.keyframe_insert(data_path="location", frame=start)
            knob.location.x = x+1.8
            knob.keyframe_insert(data_path="location", frame=start+35)
            text3d("Enabled label", "PROTECTION ON", (x+1.0,-0.55,2.7), 0.24, mats["teal"])
        elif i == 6:
            for k, (title, desc, color) in enumerate([
                ("OPTIMIZED", "Automatic when needed", "green"),
                ("SELECT SITES", "Choose specific websites", "blue2"),
                ("ALL SITES", "Broader Edge coverage", "cyan")
            ]):
                xx = x + (k-1)*2.75
                card = cube("Protection mode card", (xx,0.0,4.15), (2.45,0.3,3.65), mats["white"], 0.15)
                cube("Mode colour stripe", (xx,-0.2,5.55), (2.12,0.04,0.12), mats[color], 0.03)
                text3d("Mode title", title, (xx,-0.22,4.72), 0.23, mats["blue"])
                text3d("Mode note", desc, (xx,-0.22,3.85), 0.18, mats["muted"])
                ico("Mode marker", (xx,-0.35,2.95), (0.25,0.14,0.25), mats[color], 2)
        elif i == 7:
            shield = ico("Shield body", (x,0.1,4.2), (1.85,0.48,2.25), mats["teal"], 1)
            # Distinct layered geometry gives the shield a clear silhouette.
            cube("Shield inset", (x,-0.44,4.2), (1.95,0.16,2.05), mats["blue2"], 0.28)
            line("Shield check", [(x-0.68,-0.61,4.15),(x-0.12,-0.62,3.55),(x+0.78,-0.62,4.62)], 0.14, mats["white"])
            ring = torus("Shield halo", (x,0.5,4.2), 3.1, 0.05, mats["orange"], (math.radians(72),0,0))
            animate_float(ring, start, end, 0.05, 0.5)
            animate_float(shield, start, end, 0.16, 0.10)
            text3d("Active status", "SHIELD ACTIVE", (x,-0.8,2.45), 0.30, mats["blue"])
        elif i == 8:
            label_card("Before and after IP", x, 0.1, 4.1, 8.0, 4.6, "PUBLIC IP CHECK", "Illustrative example addresses", mats, "cyan")
            for k, (head, ip, col) in enumerate([
                ("BEFORE", "203.0.113.42", "orange"),
                ("AFTER", "198.51.100.18", "green")
            ]):
                xx = x+(k-0.5)*3.65
                cube("IP comparison card", (xx,-0.48,4.0), (3.2,0.12,1.65), mats["cream"], 0.12)
                text3d("IP comparison heading", head, (xx,-0.58,4.52), 0.20, mats[col])
                text3d("IP comparison value", ip, (xx,-0.59,3.85), 0.21, mats["blue"])
            text3d("IP check caveat", "Use a trusted checker; results can vary", (x,-0.6,2.75), 0.20, mats["muted"])
        elif i == 9:
            label_card("Usage and limits", x, 0.15, 4.25, 7.8, 4.6, "KNOW THE LIMITS", "A privacy layer, not total anonymity", mats, "orange")
            for k, (big, small, col) in enumerate([
                ("5 GB", "per month", "cyan"),
                ("EDGE", "browser traffic", "blue2"),
                ("NOT", "anonymous", "red")
            ]):
                xx = x+(k-1)*2.55
                cube("Limit card", (xx,-0.48,3.75), (2.25,0.18,1.65), mats["cream"], 0.13)
                text3d("Limit value", big, (xx,-0.60,4.08), 0.38, mats[col])
                text3d("Limit descriptor", small, (xx,-0.60,3.48), 0.20, mats["ink"])

    scene = bpy.context.scene
    scene.camera = camera
    camera.location = (0, -24.5, 12.6)
    target = Vector((0.0, 0.0, 4.7))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_x = camera.driver_add("location", 0)
    camera_x.driver.expression = "28*floor((frame-1)/270)"
    scene.frame_start = 1
    scene.frame_end = TOTAL_FRAMES
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.render.filepath = "//"
    scene.view_settings.view_transform = "AgX"
    scene.camera.data.lens = 50
    scene.camera.data.dof.use_dof = False
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.16,0.24,0.31)
    # Crisp but soft-edged presentation, with high-quality contact shading.
    scene.render.resolution_percentage = 100
    scene.render.image_settings.color_depth = "8"
    scene.render.film_transparent = False
    scene.render.engine = "BLENDER_EEVEE"
    scene.frame_set(1)
    bpy.context.view_layer.update()
    return scene

def audit(scene, outdir):
    os.makedirs(outdir, exist_ok=True)
    cam = scene.camera
    bad = []
    for frame in range(1, TOTAL_FRAMES+1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        vals = list(cam.matrix_world.translation)
        if not all(math.isfinite(v) for v in vals):
            bad.append(frame)
            break
    if bad:
        raise RuntimeError("Non-finite camera transform at frame %d" % bad[0])
    scene.frame_set(1)
    blend_path = os.path.join(outdir, OUT_NAME + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    report = {
        "status": "PASS",
        "duration_seconds": DURATION,
        "frame_count": TOTAL_FRAMES,
        "fps": FPS,
        "resolution": [WIDTH, HEIGHT],
        "renderer": "Blender Eevee Next",
        "shots": [{"title": s[0], "descriptor": s[1]} for s in SHOTS],
        "camera_transform_audit": "2700 frames checked; all finite",
        "editable_project": os.path.basename(blend_path)
    }
    with open(os.path.join(outdir, "audit.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print("AUDIT_PASS: 2700 frames; 720x1280; 30 FPS; 90 seconds")

def render_segment(scene, seg, outdir):
    if seg < 0 or seg > 5:
        raise ValueError("segment-index must be between 0 and 5")
    os.makedirs(outdir, exist_ok=True)
    start = seg * SEGMENT_FRAMES + 1
    end = start + SEGMENT_FRAMES - 1
    scene.frame_start = start
    scene.frame_end = end
    frames_dir = os.path.join(outdir, "segment_%02d_frames" % seg)
    os.makedirs(frames_dir, exist_ok=True)
    prefix = os.path.join(frames_dir, "frame_")
    scene.render.filepath = prefix
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.fps = FPS
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.frame_set(start)
    print("RENDER_START segment=%d frames=%d-%d" % (seg, start, end), flush=True)
    bpy.ops.render.render(animation=True)
    path = os.path.join(outdir, "segment_%02d.mp4" % seg)
    cmd = [
        "ffmpeg", "-y", "-framerate", str(FPS), "-start_number", str(start),
        "-i", prefix + "%04d.png", "-frames:v", str(SEGMENT_FRAMES),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", path
    ]
    print("ENCODE_START", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)
    if not os.path.exists(path) or os.path.getsize(path) < 100000:
        raise RuntimeError("Render output missing or unexpectedly small: " + path)
    print("RENDER_SECTION_VERIFIED", path, os.path.getsize(path), flush=True)

def main():
    args = parse_args()
    scene = build_scene()
    if args.mode == "audit":
        audit(scene, args.output_dir)
    else:
        render_segment(scene, args.segment_index, args.output_dir)

if __name__ == "__main__":
    main()
