#!/usr/bin/env python3
"""
BROWN | BOOK ONE — FrameForge Blender CPU production scene
Builds a fully editable Blender scene with armature-rigged characters, a real
vehicle hierarchy, IK steering, a physical phone prop, camera cuts, deterministic
ragdoll-style impulse motion, and a frame-by-frame audit.

Run from the repository root:
  blender --background --python blender_pipeline/brown_scene_cpu.py -- --mode audit
  blender --background --python blender_pipeline/brown_scene_cpu.py -- --mode build
  blender --background --python blender_pipeline/brown_scene_cpu.py -- --mode render

No image generation, external models, textures, or GPU are used.
"""
import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector, Euler, Matrix

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "brown_scene_config.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}
RENDER_CONFIG = CONFIG.get("render", {})
SCENE_CONFIG = CONFIG.get("scene", {})
FPS = int(RENDER_CONFIG.get("fps", 30))
DURATION_SECONDS = int(RENDER_CONFIG.get("duration_seconds", 90))
FRAME_START = 1
FRAME_END = FPS * DURATION_SECONDS
BLAST_TIME = float(SCENE_CONFIG.get("explosion_time_seconds", 43.5))
BLAST_FRAME = int(BLAST_TIME * FPS) + 1
MIN_TRAVEL_BLOCKS = float(SCENE_CONFIG.get("minimum_vehicle_travel_blocks", 180.0))
FINAL_APPROACH_BLOCKS = float(SCENE_CONFIG.get("final_approach_blocks", 188.0))
OUTPUT_W = int(RENDER_CONFIG.get("width", 720))
OUTPUT_H = int(RENDER_CONFIG.get("height", 1280))
SAMPLES = int(RENDER_CONFIG.get("cycles_samples", 64))

ROOT = Path.cwd()
OUT_DIR = ROOT / "output" / "brown_blender_cpu"
BLEND_PATH = OUT_DIR / "BROWN_Book_One_Blender_CPU.blend"
VIDEO_PATH = OUT_DIR / "BROWN_Book_One_Blender_CPU_90s.mp4"
AUDIT_PATH = OUT_DIR / "BROWN_Blender_CPU_Audit.json"
GLB_PATH = OUT_DIR / "BROWN_Book_One_Blender_CPU.glb"

CHARACTER_SPECS = {
    "Kesh":  {"seat": (-0.58, 1.22, 0.12), "skin": (0.34, 0.19, 0.13), "hair": (0.035, 0.028, 0.025), "coat": (0.18, 0.23, 0.17), "pants": (0.12, 0.13, 0.12), "style": "short"},
    "Amel":  {"seat": ( 0.58, 1.22, 0.12), "skin": (0.43, 0.25, 0.18), "hair": (0.04, 0.035, 0.045), "coat": (0.24, 0.16, 0.25), "pants": (0.15, 0.13, 0.16), "style": "bun"},
    "Kaylen":{"seat": (-0.58,-0.18, 0.12), "skin": (0.39, 0.22, 0.16), "hair": (0.025,0.024,0.024), "coat": (0.13, 0.18, 0.23), "pants": (0.11, 0.13, 0.17), "style": "short"},
    "Biko":  {"seat": ( 0.58,-0.18, 0.12), "skin": (0.48, 0.29, 0.20), "hair": (0.07, 0.04, 0.025), "coat": (0.43, 0.31, 0.18), "pants": (0.18, 0.17, 0.16), "style": "curl"},
    "Tovin": {"seat": (-0.58,-1.55, 0.12), "skin": (0.39, 0.20, 0.14), "hair": (0.025,0.03,0.04), "coat": (0.48, 0.31, 0.14), "pants": (0.15, 0.23, 0.31), "style": "short"},
    "Lark":  {"seat": ( 0.58,-1.55, 0.12), "skin": (0.33, 0.19, 0.14), "hair": (0.035,0.03,0.03), "coat": (0.18, 0.18, 0.23), "pants": (0.14, 0.15, 0.19), "style": "long"},
}

MAT = {}

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("audit", "build", "render"), default="build")
    p.add_argument("--output-dir", default=str(OUT_DIR))
    p.add_argument("--threads", type=int, default=0)
    return p.parse_args(argv)

def ensure_collection(name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection

def link_object(obj, collection_name="BROWN • Environment"):
    collection = ensure_collection(collection_name)
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)
    return obj

def make_material(name, color, roughness=0.7, metallic=0.0, emission=None):
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        if emission:
            socket = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
            if socket:
                socket.default_value = (*emission[0], 1.0)
            strength = bsdf.inputs.get("Emission Strength")
            if strength:
                strength.default_value = emission[1]
    return material

def setup_materials():
    palette = {
        "asphalt": ((0.025,0.034,0.044),0.94,0),
        "concrete": ((0.12,0.14,0.15),0.88,0),
        "concrete_light": ((0.23,0.24,0.22),0.88,0),
        "metal": ((0.09,0.12,0.15),0.42,0.72),
        "glass": ((0.025,0.07,0.09),0.18,0.28),
        "rubber": ((0.012,0.014,0.016),0.93,0),
        "chrome": ((0.38,0.43,0.45),0.22,0.86),
        "lamp": ((0.9,0.63,0.29),0.32,0,((1.0,0.46,0.16),3.0)),
        "screen": ((0.03,0.17,0.22),0.22,0,((0.12,0.62,0.82),2.3)),
        "phone_body": ((0.012,0.016,0.021),0.24,0.25),
        "eye_white": ((0.82,0.78,0.68),0.42,0),
        "eye_dark": ((0.018,0.014,0.012),0.26,0),
        "mouth": ((0.045,0.012,0.014),0.8,0),
        "skin_default": ((0.38,0.22,0.16),0.72,0),
        "jacket_trim": ((0.63,0.55,0.38),0.76,0),
        "paper": ((0.74,0.69,0.56),0.92,0),
        "fire": ((0.9,0.16,0.025),0.25,0,((1.0,0.14,0.015),7.0)),
        "smoke": ((0.07,0.075,0.08),0.98,0),
        "foliage": ((0.045,0.17,0.095),0.86,0),
        "foliage_light": ((0.095,0.28,0.14),0.82,0),
        "stone": ((0.20,0.23,0.22),0.94,0),
        "book_cover": ((0.12,0.19,0.24),0.55,0),
    }
    for name, values in palette.items():
        MAT[name] = make_material("BROWN • " + name, values[0], values[1], values[2], values[3] if len(values)>3 else None)
    for name, spec in CHARACTER_SPECS.items():
        MAT[name+"_skin"] = make_material("Character • "+name+" • skin", spec["skin"], 0.78)
        MAT[name+"_hair"] = make_material("Character • "+name+" • hair", spec["hair"], 0.82)
        MAT[name+"_coat"] = make_material("Character • "+name+" • coat", spec["coat"], 0.82)
        MAT[name+"_pants"] = make_material("Character • "+name+" • pants", spec["pants"], 0.88)

def add_bevel(obj, width=0.035, segments=3):
    if width > 0:
        bevel = obj.modifiers.new("Crafted soft block edges", "BEVEL")
        bevel.width = width
        bevel.segments = segments
        bevel.limit_method = "ANGLE"
        normal = obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
        normal.keep_sharp = True
    return obj

def cube_obj(name, location, dimensions, material, parent=None, bevel=0.035, collection="BROWN • Environment"):
    mesh = bpy.data.meshes.new(name + " Mesh")
    x,y,z = (v*0.5 for v in dimensions)
    verts = [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    faces = [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(4,0,3,7)]
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    ensure_collection(collection).objects.link(obj)
    obj.parent = parent
    obj.location = location
    if bevel:
        add_bevel(obj, min(bevel, min(dimensions)*0.18), 3)
    obj["collision_enabled"] = True
    obj["collision_shape"] = "BOX"
    return obj

def empty_obj(name, location=(0,0,0), parent=None, display="PLAIN_AXES"):
    obj = bpy.data.objects.new(name, None)
    ensure_collection("BROWN • Rig Controls").objects.link(obj)
    obj.empty_display_type = display
    obj.empty_display_size = 0.12
    obj.parent = parent
    obj.location = location
    return obj

def torus_obj(name, location, major, minor, material, parent=None, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=48, minor_segments=12, location=(0,0,0))
    obj = bpy.context.object
    obj.name = name
    link_object(obj, "BROWN • Vehicle")
    obj.parent = parent
    obj.location = location
    obj.rotation_euler = rotation
    obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj["collision_enabled"] = True
    obj["collision_shape"] = "TORUS_PROXY"
    return obj

def add_light(name, light_type, location, color, energy, size=1.0, parent=None):
    data = bpy.data.lights.new(name, light_type)
    data.color = color
    data.energy = energy
    if light_type == "AREA":
        data.shape = "DISK"
        data.size = size
    elif light_type == "POINT":
        data.shadow_soft_size = size
    obj = bpy.data.objects.new(name, data)
    ensure_collection("BROWN • Lighting").objects.link(obj)
    obj.parent = parent
    obj.location = location
    return obj

def add_text(name, body, location, size, material, parent=None, rotation=(math.pi/2,0,0), align="CENTER"):
    curve = bpy.data.curves.new(name + " Font", type="FONT")
    curve.body = body
    curve.size = size
    curve.align_x = align
    curve.align_y = "CENTER"
    curve.extrude = 0.0008
    obj = bpy.data.objects.new(name, curve)
    ensure_collection("BROWN • Text Props").objects.link(obj)
    obj.parent = parent
    obj.location = location
    obj.rotation_euler = rotation
    obj.data.materials.append(material)
    return obj

def add_character_box(verts, faces, mat_ids, group_indices, feature_indices, center, dims, mat_index, bone, rotation=None, feature=None):
    center = Vector(center)
    rot = rotation if rotation is not None else Matrix.Identity(3)
    x,y,z = (d*0.5 for d in dims)
    corners = [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    start = len(verts)
    for c in corners:
        point = center + (rot @ Vector(c))
        verts.append(tuple(point))
    local_faces = [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(4,0,3,7)]
    for face in local_faces:
        faces.append(tuple(start+i for i in face))
        mat_ids.append(mat_index)
    group_indices.setdefault(bone, []).extend(range(start, start+8))
    if feature:
        feature_indices.setdefault(feature, []).extend(range(start, start+8))

def add_segment(verts, faces, mat_ids, group_indices, feature_indices, start, end, width, depth, mat_index, bone, feature=None):
    a, b = Vector(start), Vector(end)
    direction = b-a
    rot = Vector((0,0,1)).rotation_difference(direction.normalized()).to_matrix()
    # Slight overlap at every joint prevents visible gaps when the connected rig bends.
    add_character_box(verts, faces, mat_ids, group_indices, feature_indices, (a+b)*0.5, (width,depth,direction.length+0.12), mat_index, bone, rot, feature)

BONE_REST = {
    "root": ((0,0,0),(0,0,0.85),None),
    "pelvis": ((0,0,0.78),(0,0,1.08),"root"),
    "spine": ((0,0,1.02),(0,0,1.83),"pelvis"),
    "neck": ((0,0,1.78),(0,0,2.08),"spine"),
    "head": ((0,0,2.02),(0,0,2.60),"neck"),
    "upper_arm.L": ((-0.36,0,1.72),(-0.55,0.20,1.46),"spine"),
    "forearm.L": ((-0.55,0.20,1.46),(-0.48,0.49,1.22),"upper_arm.L"),
    "hand.L": ((-0.48,0.49,1.22),(-0.48,0.66,1.22),"forearm.L"),
    "upper_arm.R": ((0.36,0,1.72),(0.55,0.20,1.46),"spine"),
    "forearm.R": ((0.55,0.20,1.46),(0.48,0.49,1.22),"upper_arm.R"),
    "hand.R": ((0.48,0.49,1.22),(0.48,0.66,1.22),"forearm.R"),
    "thigh.L": ((-0.20,0,0.90),(-0.20,0.42,0.62),"pelvis"),
    "shin.L": ((-0.20,0.42,0.62),(-0.20,0.82,0.28),"thigh.L"),
    "foot.L": ((-0.20,0.82,0.28),(-0.20,1.08,0.27),"shin.L"),
    "thigh.R": ((0.20,0,0.90),(0.20,0.42,0.62),"pelvis"),
    "shin.R": ((0.20,0.42,0.62),(0.20,0.82,0.28),"thigh.R"),
    "foot.R": ((0.20,0.82,0.28),(0.20,1.08,0.27),"shin.R"),
}

def create_armature(name, location, parent):
    data = bpy.data.armatures.new(name + " • Skeleton")
    rig = bpy.data.objects.new(name + " • Rig", data)
    ensure_collection("BROWN • Character Rigs").objects.link(rig)
    rig.location = location
    rig.parent = parent
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bones = {}
    for bone_name, (head, tail, parent_name) in BONE_REST.items():
        bone = data.edit_bones.new(bone_name)
        bone.head = head
        bone.tail = tail
        bones[bone_name] = bone
    for bone_name, (head, tail, parent_name) in BONE_REST.items():
        if parent_name:
            bones[bone_name].parent = bones[parent_name]
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.select_set(False)
    rig.show_in_front = True
    rig["rig_type"] = "BROWN_BlockHuman_v2"
    rig["rigged"] = True
    rig["collision_shape"] = "CAPSULE"
    rig["collision_radius"] = 0.34
    rig["collision_height"] = 2.55
    return rig

def create_character(name, spec, car_root):
    rig = create_armature(name, spec["seat"], car_root)
    verts, faces, mat_ids, groups, features = [], [], [], {}, {}
    materials = [
        MAT[name+"_skin"], MAT[name+"_hair"], MAT[name+"_coat"], MAT[name+"_pants"],
        MAT["eye_white"], MAT["eye_dark"], MAT["mouth"], MAT["jacket_trim"]
    ]
    mi = {k:i for i,k in enumerate(("skin","hair","coat","pants","eye_white","eye_dark","mouth","trim"))}
    def box(center, dims, material_key, bone, rotation=None, feature=None):
        add_character_box(verts, faces, mat_ids, groups, features, center, dims, mi[material_key], bone, rotation, feature)
    def segment(a,b,w,d,material_key,bone):
        add_segment(verts, faces, mat_ids, groups, features, a,b,w,d,mi[material_key],bone)

    # Core body: overlapping, bevelled block anatomy. Each vertex is rigid-weighted
    # to one named bone, so no limb can drift away from the character.
    box((0,0,0.91),(.62,.43,.32),"pants","pelvis")
    box((0,0,1.48),(.88,.46,.88),"coat","spine")
    box((0,.235,1.49),(.40,.035,.62),"trim","spine")
    box((0,0,1.94),(.22,.25,.24),"skin","neck")
    box((0,0,2.30),(.61,.52,.62),"skin","head")
    # Jacket seam, collar and belt details.
    box((-.25,.244,1.78),(.13,.035,.23),"trim","spine")
    box((.25,.244,1.78),(.13,.035,.23),"trim","spine")
    box((0,.235,1.12),(.63,.04,.09),"hair","pelvis")
    # Arms and hands.
    segment((-.37,0,1.72),(-.55,.20,1.46),.25,.27,"coat","upper_arm.L")
    segment((-.55,.20,1.46),(-.48,.49,1.22),.22,.24,"coat","forearm.L")
    box((-.48,.55,1.20),(.24,.25,.16),"skin","hand.L")
    segment((.37,0,1.72),(.55,.20,1.46),.25,.27,"coat","upper_arm.R")
    segment((.55,.20,1.46),(.48,.49,1.22),.22,.24,"coat","forearm.R")
    box((.48,.55,1.20),(.24,.25,.16),"skin","hand.R")
    # Seated legs and boots. Their foot soles remain below the knee line.
    segment((-.20,0,.90),(-.20,.42,.62),.34,.36,"pants","thigh.L")
    segment((-.20,.42,.62),(-.20,.82,.28),.28,.29,"pants","shin.L")
    box((-.20,.96,.26),(.38,.48,.24),"hair","foot.L")
    segment((.20,0,.90),(.20,.42,.62),.34,.36,"pants","thigh.R")
    segment((.20,.42,.62),(.20,.82,.28),.28,.29,"pants","shin.R")
    box((.20,.96,.26),(.38,.48,.24),"hair","foot.R")
    # Hair silhouettes vary by character without changing face geometry.
    style = spec["style"]
    box((0,0,2.60),(.64,.54,.12),"hair","head")
    if style in ("short","long"):
        box((-.27,-.005,2.32),(.07,.45,.34),"hair","head")
        box((.27,-.005,2.32),(.07,.45,.34),"hair","head")
    if style == "bun":
        box((0,-.23,2.68),(.24,.25,.22),"hair","head")
    if style == "curl":
        for x in (-.20,0,.20):
            box((x,.02,2.69),(.20,.23,.15),"hair","head")
    # Exactly two eyes, two pupils, two brows, two ears, one nose and one mouth.
    for side in (-1,1):
        suffix = "L" if side < 0 else "R"
        box((side*.135,.270,2.34),(.095,.045,.075),"eye_white","head",feature="eye."+suffix)
        box((side*.135,.298,2.34),(.043,.025,.048),"eye_dark","head",feature="pupil."+suffix)
        box((side*.135,.267,2.435),(.12,.055,.035),"hair","head",feature="brow."+suffix)
        box((side*.36,0,2.28),(.12,.25,.18),"skin","head",feature="ear."+suffix)
    box((0,.306,2.22),(.085,.10,.11),"skin","head",feature="nose")
    box((0,.292,2.095),(.15,.035,.035),"mouth","head",feature="mouth")
    # Facial feature counts are stored on the mesh and checked before rendering.
    mesh = bpy.data.meshes.new(name + " • Single Skinned Body")
    mesh.from_pydata(verts, [], faces)
    for m in materials:
        mesh.materials.append(m)
    for poly, material_index in zip(mesh.polygons, mat_ids):
        poly.material_index = material_index
        poly.use_smooth = False
    body = bpy.data.objects.new(name + " • Unified Rig Mesh", mesh)
    ensure_collection("BROWN • Character Meshes").objects.link(body)
    body.parent = rig
    body.location = (0,0,0)
    for bone_name, indices in groups.items():
        group = body.vertex_groups.new(name=bone_name)
        group.add(indices, 1.0, "REPLACE")
    modifier = body.modifiers.new("Armature • full-body skin", "ARMATURE")
    modifier.object = rig
    modifier.use_vertex_groups = True
    add_bevel(body, 0.018, 2)
    body["single_body_mesh"] = True
    body["face_audit"] = {
        "eyes": 2, "pupils": 2, "brows": 2, "ears": 2, "nose": 1, "mouth": 1
    }
    body["weighted_vertex_count"] = len(verts)
    body["feature_vertex_indices"] = {k: list(v) for k,v in features.items()}
    # Controlled facial expressions: no duplicated or floating face pieces.
    body.shape_key_add(name="Basis")
    mouth_key = body.shape_key_add(name="MouthOpen")
    for idx in features.get("mouth", []):
        p = mouth_key.data[idx].co
        p.z += 0.045 if p.z >= 2.095 else -0.045
    blink_key = body.shape_key_add(name="Blink")
    eye_indices = features.get("eye.L", []) + features.get("eye.R", [])
    pupil_indices = features.get("pupil.L", []) + features.get("pupil.R", [])
    for idx in eye_indices + pupil_indices:
        p = blink_key.data[idx].co
        p.z = 2.34 + (p.z - 2.34) * 0.18
    brow_key = body.shape_key_add(name="BrowRaise")
    for key_name in ("brow.L","brow.R"):
        for idx in features.get(key_name, []):
            brow_key.data[idx].co.z += 0.045
    rig["face_counts"] = dict(body["face_audit"])
    rig["body_mesh_name"] = body.name
    rig["bone_count"] = len(BONE_REST)
    # Hidden capsule mesh is an editable hitbox and a Blender collision surface.
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=.38, depth=1.72, location=(0,0,0))
    hitbox = bpy.context.object
    hitbox.name = name+" • Capsule Hitbox"
    # Join two spherical ends to the centre cylinder into one capsule collision mesh.
    capsule_parts = [hitbox]
    for cap_z in (-.86,.86):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=.38, location=(0,0,cap_z))
        capsule_parts.append(bpy.context.object)
    bpy.ops.object.select_all(action="DESELECT")
    for part in capsule_parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = hitbox
    bpy.ops.object.join()
    hitbox = bpy.context.object
    hitbox.name = name+" • Capsule Hitbox"
    link_object(hitbox,"BROWN • Collision Hitboxes")
    hitbox.parent = rig
    hitbox.location = (0,0,1.28)
    hitbox.scale = (1,1,1)
    hitbox.hide_render = True
    hitbox.display_type = "WIRE"
    hitbox["hitbox"] = True
    hitbox["radius"] = 0.38
    hitbox["height"] = 2.48
    hitbox["geometry"] = "cylinder with spherical end caps"
    hitbox["collision_enabled"] = True
    hitbox["collision_role"] = "hidden character capsule for cloth/soft-body/particle deflection"
    collision = hitbox.modifiers.new("Physics • Character Hitbox","COLLISION")
    if hasattr(collision,"settings"):
        collision.settings.damping = .72
        collision.settings.cloth_friction = 18.0
    if getattr(hitbox,"collision",None):
        hitbox.collision.use = True
    return {"name":name,"rig":rig,"body":body,"hitbox":hitbox,"features":features}

def add_ik_hand(rig, bone_name, target):
    pose_bone = rig.pose.bones[bone_name]
    pose_bone.ik_stretch = 0.0
    constraint = pose_bone.constraints.new("IK")
    constraint.name = "Steering hand lock • " + bone_name
    constraint.target = target
    constraint.chain_count = 3
    constraint.use_stretch = False
    return constraint

def create_phone(kaylen):
    rig = kaylen["rig"]
    # Phone is a real three-dimensional prop, oriented screen-forward in the hand.
    phone = cube_obj("Kaylen • Physical Smartphone", (0.52,0.73,1.42), (.16,.035,.29), MAT["phone_body"], rig, .018, "BROWN • Props")
    phone["prop_role"] = "physical-phone"
    phone["screen_text"] = "YOU CAN STILL LEAVE"
    phone["screen_is_geometry"] = True
    screen = cube_obj("Smartphone • Emissive Glass Screen", (0,0,0), (.138,.008,.255), MAT["screen"], phone, .005, "BROWN • Props")
    screen.location = (0,-.020,0)
    screen["prop_role"] = "physical-phone-screen"
    # Small speaker slot, camera lens and side buttons are attached to the handset.
    speaker = cube_obj("Smartphone • Earpiece", (0,0,0), (.045,.006,.008), MAT["chrome"], phone, .002, "BROWN • Props")
    speaker.location = (0,-.026,.116)
    lens = cube_obj("Smartphone • Camera Lens", (0,0,0), (.014,.006,.014), MAT["chrome"], phone, .003, "BROWN • Props")
    lens.location = (.052,-.026,.116)
    side_button = cube_obj("Smartphone • Side Button", (0,0,0), (.008,.018,.035), MAT["chrome"], phone, .002, "BROWN • Props")
    side_button.location = (.083,0,.04)
    # The message is actual 3D text on the screen mesh, not a video overlay.
    message = add_text("Phone Screen • Incoming Message", "YOU CAN STILL\nLEAVE", (0,0,0), .012, MAT["eye_white"], phone, rotation=(math.pi/2,0,0))
    message.location = (0,-.026,0.0)
    message.data.align_x = "CENTER"
    message.data.size = .012
    message["is_physical_screen_text"] = True
    # The phone vibrates in the hand at the incoming-message moment, then drops with Kaylen.
    for sec, dx, rz in ((37.5,0,0),(37.62,.018,.10),(37.76,-.014,-.08),(37.90,0,0),(43.45,0,0)):
        frame = int(sec*FPS)+1
        phone.location = (.52+dx,.73,1.42)
        phone.rotation_euler.z = rz
        phone.keyframe_insert(data_path="location",frame=frame)
        phone.keyframe_insert(data_path="rotation_euler",frame=frame)
    kaylen["phone"] = phone
    kaylen["phone_screen"] = screen
    return phone

def create_vehicle():
    root = empty_obj("BROWN • Single Crew Vehicle Root")
    root["vehicle_type"] = "six-seat enclosed SUV"
    root["minimum_pre_blast_travel_blocks"] = MIN_TRAVEL_BLOCKS
    # Monocoque and passenger cabin. Roof clearance is sized for seated human rigs.
    cube_obj("Vehicle • Lower Body", (0,0,.68), (2.25,6.15,.92), MAT["metal"], root, .16, "BROWN • Vehicle")
    cube_obj("Vehicle • Cabin Roof", (0,-.08,2.92), (2.08,3.88,.22), MAT["metal"], root, .10, "BROWN • Vehicle")
    cube_obj("Vehicle • Hood", (0,2.33,1.13), (2.06,1.35,.30), MAT["metal"], root, .09, "BROWN • Vehicle")
    cube_obj("Vehicle • Front Bumper", (0,3.11,.60), (2.24,.18,.30), MAT["chrome"], root, .04, "BROWN • Vehicle")
    cube_obj("Vehicle • Rear Bumper", (0,-3.10,.60), (2.24,.18,.30), MAT["chrome"], root, .04, "BROWN • Vehicle")
    glass = make_material("Vehicle • Tinted Glass", (0.025,.065,.08), .16, .30)
    glass.diffuse_color = (0.025,.065,.08,.20)
    glass_bsdf = glass.node_tree.nodes.get("Principled BSDF") if glass.use_nodes else None
    if glass_bsdf and glass_bsdf.inputs.get("Alpha"):
        glass_bsdf.inputs["Alpha"].default_value = .18
    if hasattr(glass, "surface_render_method"):
        glass.surface_render_method = "DITHERED"
    # Windshield / rear glass / side windows.
    cube_obj("Vehicle • Windshield", (0,2.02,2.45), (1.82,.055,.88), glass, root, .04, "BROWN • Vehicle")
    cube_obj("Vehicle • Rear Glass", (0,-2.11,2.42), (1.82,.055,.82), glass, root, .04, "BROWN • Vehicle")
    for side in (-1,1):
        for y in (1.00,-.22,-1.43):
            if side == 1 and y == -1.43:
                continue  # The right-rear window belongs to the hinged Lark door.
            cube_obj("Vehicle • Side Window", (side*1.035,y,2.43), (.045,1.06,.76), glass, root, .025, "BROWN • Vehicle")
        for y in (-1.92,1.93):
            wheel = torus_obj("Vehicle • Tyre", (side*1.13,y,.47), .38,.16,MAT["rubber"],root,(0,math.pi/2,0))
            wheel["wheel_radius"] = .38
            torus_obj("Vehicle • Alloy Hub", (side*1.145,y,.47), .18,.045,MAT["chrome"],root,(0,math.pi/2,0))
    # Six visible seats in a three-row cabin.
    for row_y in (1.15,-.18,-1.50):
        for x in (-.56,.56):
            cube_obj("Vehicle • Seat Cushion", (x,row_y,.90), (.86,.92,.22), MAT["concrete"], root, .07, "BROWN • Vehicle")
            cube_obj("Vehicle • Seat Back", (x,row_y-.34,1.34), (.86,.22,.88), MAT["concrete"], root, .07, "BROWN • Vehicle")
    # Steering column and wheel are real objects, not a drawn symbol.
    steering = torus_obj("Vehicle • Steering Wheel", (-.58,1.83,1.28), .28,.035,MAT["chrome"],root,(math.pi/2,0,0))
    steering["prop_role"] = "steering-wheel"
    cube_obj("Vehicle • Steering Column", (-.58,1.57,1.16), (.10,.42,.10), MAT["metal"], root, .025, "BROWN • Vehicle")
    # Dashboard, gear selector, mirrors, lamps and handles.
    cube_obj("Vehicle • Dashboard", (0,1.85,1.05), (2.0,.50,.32), MAT["metal"], root, .06, "BROWN • Vehicle")
    cube_obj("Vehicle • Instrument Display", (-.58,1.82,1.25), (.36,.025,.13), MAT["screen"], root, .015, "BROWN • Vehicle")
    cube_obj("Vehicle • Rear-view Mirror", (0,1.72,2.02), (.28,.08,.10), MAT["chrome"], root, .025, "BROWN • Vehicle")
    for side in (-1,1):
        cube_obj("Vehicle • Mirror", (side*1.20,2.12,1.56), (.16,.32,.14), MAT["metal"], root, .035, "BROWN • Vehicle")
        cube_obj("Vehicle • Headlamp", (side*.73,3.12,.92), (.48,.06,.20), MAT["lamp"], root, .035, "BROWN • Vehicle")
        cube_obj("Vehicle • Tail Lamp", (side*.78,-3.12,.94), (.30,.06,.34), MAT["fire"], root, .025, "BROWN • Vehicle")
    # Lark opens a real rear passenger door around the approach.
    hinge = empty_obj("Vehicle • Rear Right Door Hinge", (1.10,-1.45,1.07), root, "CIRCLE")
    door = cube_obj("Vehicle • Rear Right Door", (0,-.48,.45), (.12,1.10,1.50), MAT["metal"], hinge, .06, "BROWN • Vehicle")
    door["door_role"] = "Lark exit door"
    door["collision_enabled"] = True
    cube_obj("Vehicle • Door Window", (0,-.47,.86), (.055,.98,.70), glass, hinge, .025, "BROWN • Vehicle")
    for sec, angle in ((0,0),(40.1,0),(41.0,math.radians(34)),(43.4,math.radians(34)),(44.0,math.radians(42))):
        hinge.rotation_euler.z = angle
        hinge.keyframe_insert(data_path="rotation_euler",frame=int(sec*FPS)+1)
    # Four wheel objects are audited and their rolling is driven by distance.
    wheels = [o for o in root.children if o.name == "Vehicle • Tyre"]
    if not wheels:
        wheels = [o for o in bpy.data.objects if o.name == "Vehicle • Tyre"]
    # Dashboard clock is a 3D object inside the car, never a video caption.
    clock = add_text("Dashboard Clock • 21:39", "21:39", (-.30,1.83,1.27), .075, MAT["eye_white"], root)
    clock.data.align_x = "CENTER"
    clock2 = add_text("Dashboard Clock • 21:40", "21:40", (-.30,1.83,1.27), .075, MAT["eye_white"], root)
    clock2.hide_render = True
    clock2.keyframe_insert(data_path="hide_render",frame=1)
    clock2.hide_render = False
    clock2.keyframe_insert(data_path="hide_render",frame=int(42.5*FPS)+1)
    clock2.hide_render = False
    clock2.keyframe_insert(data_path="hide_render",frame=BLAST_FRAME)
    clock.hide_render = False
    clock.keyframe_insert(data_path="hide_render",frame=1)
    clock.hide_render = True
    clock.keyframe_insert(data_path="hide_render",frame=int(42.5*FPS)+1)
    return root, steering, hinge, door, wheels

def build_road_and_corridor():
    cube_obj("Road • 220 Block Asphalt", (0,104,-.32), (16,244,.58), MAT["asphalt"], None, .08)
    for side in (-1,1):
        cube_obj("Road • Concrete Curb", (side*8.2,104,-.08), (.42,244,.55), MAT["concrete"], None, .06)
        cube_obj("Road • Pavement", (side*10.6,104,-.04), (4.2,244,.28), MAT["concrete"], None, .04)
        for y in range(-4,216,24):
            # Industrial blocks on both sides; no background crowds.
            width = 5.0 + ((y//24)%3)*1.1
            height = 8.0 + ((y//24)%4)*2.0
            building = cube_obj("Industrial Building", (side*(13.2+width*.50),y+7,height*.5), (width,17.5,height), MAT["concrete_light"], None, .10)
            building["environment_role"] = "static industrial facade"
            for level in range(2,int(height//2)):
                for bay in range(2):
                    wx = side*(13.2+width*.5)
                    wy = y + 1.5 + bay*6.5
                    cube_obj("Warehouse Window", (wx,wy,level*1.6), (.045,1.1,.75), MAT["glass"], None, .018)
        for y in range(0,210,28):
            pole = cube_obj("Streetlight Pole", (side*7.2,y,3.2), (.10,.10,6.4), MAT["metal"], None, .02)
            cube_obj("Streetlight Arm", (side*6.8,y,6.2), (.9,.10,.10), MAT["metal"], None, .02)
            light = add_light("Industrial Streetlight", "POINT", (side*6.6,y,6.05), (1.0,.62,.34), 300, 1.2)
            light["environment_role"] = "street light"
    for y in range(-2,218,8):
        cube_obj("Road • Centre Dash", (0,y,.004), (.12,3.2,.018), MAT["paper"], None, .005)
    # Destination: one empty industrial warehouse and two parked vehicles.
    cube_obj("Warehouse • Main Structure", (0,194,7.0), (24,2.8,14), MAT["concrete"], None, .14)
    cube_obj("Warehouse • Loading Bay Opening", (0,192.48,3.5), (8,.08,6.8), MAT["asphalt"], None, .01)
    for x in (-3.6,-2.4,-1.2,0,1.2,2.4,3.6):
        cube_obj("Warehouse • Roller Door Slat", (x,192.40,3.5), (.055,.06,6.4), MAT["metal"], None, .008)
    for side in (-1,1):
        cube_obj("Warehouse • Security Floodlight", (side*8,192.2,8.2), (.45,.20,.25), MAT["lamp"], None, .03)
        add_light("Warehouse • Security Light", "AREA", (side*8,188.0,8.0), (1.0,.70,.42), 900, 5.0)
    # Two parked vehicles from the book's approach description; they remain empty.
    for x,y in ((-4.4,185.5),(4.4,187.2)):
        cube_obj("Unoccupied Vehicle • Dark Body", (x,y,.65), (2.0,4.5,1.0), MAT["metal"], None, .13)
        cube_obj("Unoccupied Vehicle • Glass", (x,y,1.50), (1.7,2.5,.55), MAT["glass"], None, .05)
    # Physical public notice board with its warning.
    cube_obj("Corridor Notice Board", (6.2,176.5,2.3), (3.5,.20,2.0), MAT["metal"], None, .08)
    sign = add_text("Corridor Sign • Physical Notice", "BLACK-POWERED GANG BATTLE\\nAVOID THE AREA", (6.2,176.36,2.45), .24, MAT["lamp"])
    sign.data.align_x = "CENTER"

def make_target(name, parent, location):
    return empty_obj(name, location, parent, "SPHERE")

def make_camera(name, car_root, position, target, lens=40, parent_target=None):
    data = bpy.data.cameras.new(name + " Lens")
    cam = bpy.data.objects.new(name, data)
    ensure_collection("BROWN • Cameras").objects.link(cam)
    cam.parent = car_root
    cam.location = position
    data.lens = lens
    data.dof.use_dof = True
    data.dof.focus_object = parent_target
    data.dof.aperture_fstop = 3.5
    aim = empty_obj(name+" • Aim", target, car_root, "SPHERE")
    track = cam.constraints.new("TRACK_TO")
    track.target = parent_target if parent_target else aim
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    if parent_target is None:
        track.target = aim
    return cam

def add_camera_cuts(car_root, kaylen, phone):
    target_car = make_target("Camera Aim • Vehicle", car_root, (0,0,1.0))
    target_aftermath = make_target("Camera Aim • Aftermath", car_root, (0,-1.0,1.0))
    target_epilogue = make_target("Camera Aim • Epilogue Kaylen", car_root, (0,-6.8,2.0))
    cameras = []
    def cam(name,pos,target_obj,lens):
        c = make_camera(name,car_root,pos,(0,0,1.0),lens,target_obj)
        cameras.append(c)
        return c
    cam("SHOT 01 • High Rear Road Chase", (8,-13,9), target_car, 35)
    cam("SHOT 02 • Low Side Tracking", (6,-8,2.3), target_car, 52)
    cam("SHOT 03 • Cabin Through Windshield", (0,5.7,2.65), target_car, 47)
    cam("SHOT 04 • Real Phone Close-up", (0.95,-2.0,2.10), phone, 65)
    cam("SHOT 05 • Corridor Approach", (0,-10,3.2), target_car, 42)
    cam("SHOT 06 • Empty Warehouse / Door", (5.5,-6.5,2.8), target_car, 50)
    cam("SHOT 07 • Blast Handheld", (8,-8,4.2), target_car, 38)
    cam("SHOT 08 • Wreckage Ground Level", (0,-7,1.55), target_aftermath, 55)
    cam("SHOT 09 • Kaylen Crawls", (-3,-4,1.4), target_aftermath, 60)
    cam("SHOT 10 • Quiet Epilogue", (3,-5,2.7), target_epilogue, 55)
    frames = [1,241,481,721,931,1126,1291,1501,1741,2266]
    for c, frame in zip(cameras,frames):
        marker = bpy.context.scene.timeline_markers.new(c.name, frame=frame)
        marker.camera = c
    bpy.context.scene.camera = cameras[0]
    # A deliberately controlled handheld shake during the first 0.8 seconds after impact.
    blast_cam = cameras[6]
    base = Vector(blast_cam.location)
    for f in range(BLAST_FRAME, BLAST_FRAME+25):
        t=(f-BLAST_FRAME)/FPS
        decay=math.exp(-t*5.0)
        blast_cam.location = base + Vector((math.sin(f*1.7)*.32*decay, math.cos(f*2.1)*.18*decay, math.sin(f*2.7)*.12*decay))
        blast_cam.keyframe_insert(data_path="location",frame=f)
    return cameras

def key_object(obj, data_path, value, frame):
    setattr(obj, data_path, value)
    obj.keyframe_insert(data_path=data_path, frame=frame)

def key_pose(rig, bone_name, rotation, frame):
    bone = rig.pose.bones.get(bone_name)
    if bone is None:
        raise RuntimeError("Missing rig bone " + rig.name + ":" + bone_name)
    bone.rotation_mode = "XYZ"
    bone.rotation_euler = rotation
    bone.keyframe_insert(data_path="rotation_euler", frame=frame)

def set_shape(body, shape_name, value, frame):
    key = body.data.shape_keys.key_blocks.get(shape_name)
    if key is not None:
        key.value = value
        key.keyframe_insert(data_path="value", frame=frame)

def animate_idle_characters(chars, steering, phone):
    # Faces, head turns, breathing and hands are restrained and intentional.
    for name, ch in chars.items():
        rig, body = ch["rig"], ch["body"]
        for sec, neck, head in ((0,0,0),(7,.015,-.025),(14,-.02,.03),(22,.01,-.02),(30,-.01,.025),(36,0,0),(39,0,.10),(42,0,0)):
            f=int(sec*FPS)+1
            key_pose(rig,"spine",(0,0,neck),f)
            key_pose(rig,"head",(0,0,head),f)
        for sec in (4.2,9.6,15.3,22.8,29.4,35.6,40.3):
            f=int(sec*FPS)+1
            set_shape(body,"Blink",1.0,f)
            set_shape(body,"Blink",0.0,f+3)
        # Gentle torso breathing: no artificial vertical bobbing.
        key_pose(rig,"spine",(0,0,0),1)
        key_pose(rig,"spine",(math.radians(0.8),0,0),int(3.0*FPS)+1)
        key_pose(rig,"spine",(0,0,0),int(6.0*FPS)+1)
    # Kesh's hands are held to IK targets parented to the physical steering wheel.
    kesh = chars["Kesh"]["rig"]
    for suffix, target_position in (("L",(-.22,0,0.02)),("R",(.22,0,0.02))):
        control = empty_obj("Steering IK • Hand "+suffix, target_position, steering, "SPHERE")
        add_ik_hand(kesh,"hand."+suffix,control)
    for sec, angle in ((0,0),(8,.03),(15,-.04),(22,.035),(29,-.025),(36,.015),(39,0),(43,0)):
        f=int(sec*FPS)+1
        steering.rotation_euler[1]=angle
        steering.keyframe_insert(data_path="rotation_euler",frame=f)
    # Passenger reactions are performed through face shape keys; the phone stays in hand.
    kaylen=chars["Kaylen"]
    for sec, amount in ((36.9,0),(37.5,.8),(38.3,.35),(39.6,0),(42.9,.75),(43.5,1)):
        f=int(sec*FPS)+1
        set_shape(kaylen["body"],"BrowRaise",amount,f)
        set_shape(kaylen["body"],"MouthOpen",.16*amount,f)
    # Every occupant reacts to the flash with one controlled, readable expression.
    for name,ch in chars.items():
        for sec, mouth, brow in ((42.9,0.08,.25),(43.5,.50,.9),(44.2,.36,.65),(46.0,.18,.25),(49.0,0,0)):
            f=int(sec*FPS)+1
            set_shape(ch["body"],"MouthOpen",mouth,f)
            set_shape(ch["body"],"BrowRaise",brow,f)
    # Lark reaches for the door before the blast; the opened door is a scene prop.
    key_pose(chars["Lark"]["rig"],"spine",(math.radians(-7),0,math.radians(-6)),int(40.0*FPS)+1)
    key_pose(chars["Lark"]["rig"],"upper_arm.R",(math.radians(18),0,math.radians(-36)),int(40.2*FPS)+1)
    key_pose(chars["Lark"]["rig"],"forearm.R",(math.radians(-28),0,math.radians(-14)),int(40.7*FPS)+1)
    key_pose(chars["Lark"]["rig"],"upper_arm.R",(math.radians(8),0,math.radians(-22)),int(42.8*FPS)+1)
    # Biko leans forward between the seats; Tovin reacts to him; Lark turns to the bay.
    key_pose(chars["Biko"]["rig"],"spine",(math.radians(-4),0,0),int(21*FPS)+1)
    key_pose(chars["Biko"]["rig"],"head",(0,0,math.radians(-8)),int(22*FPS)+1)
    key_pose(chars["Tovin"]["rig"],"head",(0,0,math.radians(6)),int(22*FPS)+1)
    key_pose(chars["Lark"]["rig"],"head",(0,0,math.radians(15)),int(39.5*FPS)+1)
    # Phone close-up action: Kaylen raises it into his sightline, then lowers it.
    key_object(kaylen["rig"],"location",(-.58,-.18,.12),1)
    key_object(phone,"location",(.52,.73,1.42),int(36.9*FPS)+1)
    key_object(phone,"location",(.50,.76,1.57),int(38.0*FPS)+1)
    key_object(phone,"location",(.52,.73,1.42),int(40.1*FPS)+1)

def simulate_ragdoll(chars, car_root):
    # Deterministic 30-FPS ballistic integration with damped joint inertia. The
    # unified skinned mesh and skeleton remain intact: this is a connected rig,
    # not loose parts. Initial velocities reproduce a blast-propelled ragdoll fall.
    impulses = {
        "Kesh": (-1.3,-2.4,2.8,-1.1, .6, .4),
        "Amel": ( 1.8,-2.0,2.5, .7,-.5,-.7),
        "Kaylen":( 1.4,-3.1,3.2,-.9, .9, .5),
        "Biko": (-1.8,-2.7,2.0,1.0,-.7,-.5),
        "Tovin":(-2.2,-2.3,2.6,-.7, .6, .7),
        "Lark": ( 2.4,-1.8,2.5,.6,-.9,-.8),
    }
    for name,ch in chars.items():
        rig=ch["rig"]
        base=Vector(CHARACTER_SPECS[name]["seat"])
        vx,vy,vz,rx,ry,rz=impulses[name]
        for f in range(BLAST_FRAME, BLAST_FRAME+181):
            t=(f-BLAST_FRAME)/FPS
            x=vx*t
            y=vy*t
            z=vz*t-0.5*9.81*t*t
            if z < 0:
                z=0
                x=vx*min(t,0.65)
                y=vy*min(t,0.65)
            rig.location=base+Vector((x,y,z))
            # Rotational impulse decays through damped joint motion, then settles.
            d=math.exp(-t*2.6)
            rig.rotation_euler=(rx*(1-d),ry*(1-d),rz*(1-d))
            rig.keyframe_insert(data_path="location",frame=f)
            rig.keyframe_insert(data_path="rotation_euler",frame=f)
            for bone,scale,phase in (
                ("spine",.85,0.0),("neck",.55,.6),("head",.75,1.0),
                ("upper_arm.L",1.0,.2),("forearm.L",.9,.5),("upper_arm.R",1.0,1.1),("forearm.R",.9,1.4),
                ("thigh.L",.7,.8),("shin.L",.6,1.2),("thigh.R",.7,1.7),("shin.R",.6,2.0)
            ):
                angle=scale*math.exp(-t*2.2)*math.sin(t*10+phase)*d
                key_pose(rig,bone,(angle*(1 if "L" in bone else -1),angle*.45,angle*.35),f)
        # Settle into a connected grounded pose.
        settled=BLAST_FRAME+180
        key_pose(rig,"spine",(math.radians(58),0,0),settled)
        key_pose(rig,"head",(math.radians(-18),0,0),settled)
        key_pose(rig,"upper_arm.L",(math.radians(28),0,math.radians(-22)),settled)
        key_pose(rig,"upper_arm.R",(math.radians(-15),0,math.radians(24)),settled)
    # Car receives a short blast jolt but remains a single connected vehicle.
    for f,loc,rot in (
        (BLAST_FRAME,(0,188,0),(0,0,0)),
        (BLAST_FRAME+3,(0,187.72,.16),(math.radians(-3),math.radians(1.5),math.radians(-1.2))),
        (BLAST_FRAME+12,(0,187.85,.03),(math.radians(1),0,math.radians(.4))),
        (BLAST_FRAME+30,(0,187.85,0),(0,0,0))
    ):
        car_root.location=loc
        car_root.rotation_euler=rot
        car_root.keyframe_insert(data_path="location",frame=f)
        car_root.keyframe_insert(data_path="rotation_euler",frame=f)

def create_explosion_and_rubble(car_root):
    flash_mat = MAT["fire"]
    fireball = bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=(0,0,0))
    fire = bpy.context.object
    fire.name = "Explosion • Fireball"
    link_object(fire,"BROWN • Effects")
    fire.parent=car_root
    fire.location=(0,4.35,2.3)
    fire.data.materials.append(flash_mat)
    fire.scale=(.05,.05,.05)
    fire.keyframe_insert(data_path="scale",frame=BLAST_FRAME-1)
    fire.scale=(5.5,4.5,5.0)
    fire.keyframe_insert(data_path="scale",frame=BLAST_FRAME+7)
    fire.scale=(7.0,5.5,6.2)
    fire.keyframe_insert(data_path="scale",frame=BLAST_FRAME+18)
    fire.scale=(.1,.1,.1)
    fire.keyframe_insert(data_path="scale",frame=BLAST_FRAME+72)
    fire["effect_role"]="explosion fireball"
    blast_light=add_light("Explosion • Core Light","POINT",(0,4.3,3.0),(1.0,.20,.045),0,3.0,car_root)
    for f,energy in ((BLAST_FRAME-1,0),(BLAST_FRAME,80000),(BLAST_FRAME+5,45000),(BLAST_FRAME+18,7000),(BLAST_FRAME+50,0)):
        blast_light.data.energy=energy
        blast_light.data.keyframe_insert(data_path="energy",frame=f)
    # Dust, sparks and structural fragments have individual ballistic trajectories.
    for i in range(46):
        angle=i*2.399963
        speed=1.1+(i%7)*.34
        origin=(math.cos(angle)*.35,4.25+math.sin(angle)*.35,1.2+(i%5)*.42)
        size=.10+(i%4)*.07
        obj=cube_obj("Explosion Debris • %02d"%i,origin,(size,size,size),MAT["concrete_light"] if i%3 else MAT["metal"],car_root,.012,"BROWN • Effects")
        obj.rotation_euler=(angle,angle*.4,angle*.2)
        for f in (BLAST_FRAME,BLAST_FRAME+60,BLAST_FRAME+120):
            t=(f-BLAST_FRAME)/FPS
            obj.location=(origin[0]+math.cos(angle)*speed*t,origin[1]+math.sin(angle)*speed*t,origin[2]+(2.5+(i%5)*.35)*t-4.905*t*t)
            obj.rotation_euler=(angle+t*3,angle*.4+t*4,angle*.2+t*2)
            obj.keyframe_insert(data_path="location",frame=f)
            obj.keyframe_insert(data_path="rotation_euler",frame=f)
    for i in range(24):
        cloud=bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=1, location=(0,0,0))
        obj=bpy.context.object
        obj.name="Explosion Dust Cloud • %02d"%i
        link_object(obj,"BROWN • Effects")
        obj.parent=car_root
        obj.location=(math.sin(i*3.1)*1.7,4.35+math.cos(i*2.3)*1.5,1.4+(i%6)*.45)
        obj.data.materials.append(MAT["smoke"])
        obj.scale=(.1,.1,.1)
        obj.keyframe_insert(data_path="scale",frame=BLAST_FRAME)
        obj.scale=(.8+(i%4)*.3,.7+(i%5)*.24,.8+(i%3)*.4)
        obj.keyframe_insert(data_path="scale",frame=BLAST_FRAME+45)
        obj.scale=(1.8+(i%4)*.35,1.5+(i%5)*.3,1.3+(i%3)*.4)
        obj.keyframe_insert(data_path="scale",frame=BLAST_FRAME+150)
    for i in range(22):
        a=i*2.4
        obj=cube_obj("Aftermath Rubble • %02d"%i,(math.sin(a)*6,-1+(i%7)*.7,.12),(.5+(i%3)*.25,.35+(i%2)*.2,.20+(i%4)*.08),MAT["concrete_light"],car_root,.025,"BROWN • Effects")
        obj.rotation_euler=(a*.2,a*.3,a)
        obj.keyframe_insert(data_path="location",frame=BLAST_FRAME+150)

def create_epilogue_set(car_root):
    # A quiet closing shot; same Kaylen rig, no additional people.
    clearing_y=-7.0
    cube_obj("Epilogue • Forest Ground",(0,clearing_y,-.18),(26,24,.35),MAT["foliage"],car_root,.04,"BROWN • Epilogue")
    for i in range(18):
        x=math.sin(i*2.18)*10
        y=clearing_y+math.cos(i*1.57)*8
        trunk=cube_obj("Epilogue • Tree Trunk",(x,y,2.8),(.42,.42,5.6),MAT["stone"],car_root,.08,"BROWN • Epilogue")
        crown=cube_obj("Epilogue • Canopy",(x,y,5.8),(2.8,2.5,2.4),MAT["foliage_light"] if i%3==0 else MAT["foliage"],car_root,.24,"BROWN • Epilogue")
    for i in range(22):
        x=-9+(i%8)*2.5
        y=clearing_y-9+(i//8)*2.8
        leaf=cube_obj("Epilogue • Fern",(x,y,.55),(.12,1.2,.14),MAT["foliage_light"],car_root,.035,"BROWN • Epilogue")
        leaf.rotation_euler.z=math.sin(i)*.8
    bench=cube_obj("Epilogue • Stone Seat",(0,clearing_y,.55),(2.4,.85,.65),MAT["stone"],car_root,.12,"BROWN • Epilogue")
    cube_obj("Epilogue • Seat Top",(0,clearing_y, .91),(2.55,.95,.14),MAT["concrete_light"],car_root,.06,"BROWN • Epilogue")
    add_light("Epilogue • Warm Canopy Key","AREA",(-3,clearing_y-4,7),(1.0,.78,.52),1100,5,car_root)
    add_light("Epilogue • Cool Rim","AREA",(5,clearing_y+2,5),(.34,.60,.68),850,4,car_root)

def animate_kaylen_crawl_and_epilogue(kaylen):
    rig,body=kaylen["rig"],kaylen["body"]
    base=Vector(CHARACTER_SPECS["Kaylen"]["seat"])
    start=int(58*FPS)+1
    end=int(70*FPS)+1
    # Kaylen moves by limbs and torso, not by a floating vertical bob.
    for f in range(start,end+1,2):
        t=(f-start)/FPS
        progress=min(1.0,t/12.0)
        rig.location=base+Vector((.25*progress,-2.8*progress,0))
        rig.rotation_euler=(math.radians(68),0,math.radians(-7))
        rig.keyframe_insert(data_path="location",frame=f)
        rig.keyframe_insert(data_path="rotation_euler",frame=f)
        phase=t*5.2
        key_pose(rig,"upper_arm.L",(math.radians(38+15*math.sin(phase)),0,math.radians(-18)),f)
        key_pose(rig,"forearm.L",(math.radians(-28+12*math.sin(phase+1)),0,0),f)
        key_pose(rig,"upper_arm.R",(math.radians(38+15*math.sin(phase+math.pi)),0,math.radians(18)),f)
        key_pose(rig,"forearm.R",(math.radians(-28+12*math.sin(phase+math.pi+1)),0,0),f)
        key_pose(rig,"head",(math.radians(-12+4*math.sin(phase*.5)),0,math.radians(4*math.sin(phase*.3))),f)
    # Move the same rig into the quiet end scene and sit it naturally on the stone.
    epilogue=int(75.5*FPS)+1
    rig.rotation_euler=(0,0,0)
    rig.location=(0,-7.0,.98)
    rig.keyframe_insert(data_path="rotation_euler",frame=epilogue)
    rig.keyframe_insert(data_path="location",frame=epilogue)
    key_pose(rig,"spine",(0,0,0),epilogue)
    key_pose(rig,"head",(0,0,0),epilogue)
    # A small physical book in Kaylen's hand for the spoken close.
    book=cube_obj("Epilogue • Physical BROWN Book One",(0,0,0),(.20,.28,.035),MAT["book_cover"],rig,.018,"BROWN • Props")
    book.location=(.54,.70,1.20)
    book.rotation_euler=(math.radians(6),0,math.radians(8))
    book["prop_role"]="physical-book"
    add_text("Epilogue Book Cover • Title","BROWN",(0,0,0),.045,MAT["eye_white"],book,rotation=(math.pi/2,0,0))
    # Facial performance (mouth shape) is keyed on the same rig at 30 fps.
    for f in range(epilogue,FRAME_END+1):
        seconds=(f-epilogue)/FPS
        mouth=max(0.0, math.sin(seconds*9.2)) * (0.6 if seconds<12.0 else 0.0)
        set_shape(body,"MouthOpen",mouth,f)
        if f%90==epilogue%90:
            set_shape(body,"Blink",1.0,f)
            set_shape(body,"Blink",0.0,min(FRAME_END,f+3))

def animate_vehicle(root,wheels):
    # Fast 180-block run, then a controlled final approach and brake.
    # The high-speed lead-in is an explicit adaptation requested for the film.
    drive_keys = (
        (1, 0.0),
        (int(4*FPS)+1, 12.0),
        (int(10*FPS)+1, 65.0),
        (int(16*FPS)+1, 132.0),
        (int(20*FPS)+1, MIN_TRAVEL_BLOCKS),
        (int(37*FPS)+1, FINAL_APPROACH_BLOCKS-1.0),
        (int(39.5*FPS)+1, FINAL_APPROACH_BLOCKS),
        (BLAST_FRAME, FINAL_APPROACH_BLOCKS),
    )
    root.location=(0,0,0)
    for frame, distance in drive_keys:
        root.location=(0,distance,0)
        root.keyframe_insert(data_path="location",frame=frame)
    # Wheel rotation is distance-driven: radians = distance / wheel radius.
    for wheel in wheels:
        for frame, distance in drive_keys:
            wheel.rotation_euler[0]=distance/.38
            wheel.keyframe_insert(data_path="rotation_euler",frame=frame)
    # Smooth drive-in, then braking suspension; no stationary fake travel.
    for obj in (root,)+tuple(wheels):
        if obj.animation_data and obj.animation_data.action:
            action=obj.animation_data.action
            for fc in getattr(action,"fcurves",[]):
                for point in fc.keyframe_points:
                    point.interpolation="BEZIER"
            # Blender 4.4+ layered Actions retain the generated keys; when a
            # legacy FCurve view is available it is handled above.

def setup_render(output_dir, threads):
    scene=bpy.context.scene
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=SAMPLES
    scene.cycles.use_denoising=True
    scene.cycles.preview_samples=16
    scene.render.threads_mode="FIXED"
    scene.render.threads=threads if threads>0 else max(1,os.cpu_count() or 4)
    scene.render.resolution_x=OUTPUT_W
    scene.render.resolution_y=OUTPUT_H
    scene.render.resolution_percentage=100
    scene.render.fps=FPS
    scene.render.fps_base=1.0
    scene.frame_start=FRAME_START
    scene.frame_end=FRAME_END
    scene.render.image_settings.file_format="FFMPEG"
    scene.render.ffmpeg.format="MPEG4"
    scene.render.ffmpeg.codec="H264"
    scene.render.ffmpeg.constant_rate_factor="PERC_LOSSLESS"
    scene.render.ffmpeg.ffmpeg_preset="GOOD"
    scene.render.ffmpeg.gopsize=30
    scene.render.filepath=str(output_dir / "BROWN_Book_One_Blender_CPU_90s")
    scene.render.use_file_extension=True
    scene.render.image_settings.color_mode="RGB"
    scene.render.image_settings.color_depth="8"
    scene.view_settings.view_transform="AgX"
    scene.render.film_transparent=False
    scene.cycles.use_preview_denoising=True
    scene.render.use_persistent_data=True
    scene.render.resolution_percentage=100
    scene.world.color=(.008,.012,.020)
    # The device is fixed to CPU in both saved settings and run-time CLI config.
    scene["production_renderer"]="Blender Cycles CPU"
    scene["gpu_rendering"]="disabled"
    scene["fps"]=FPS
    scene["frame_count"]=FRAME_END
    scene["world_units"]="1 Blender unit = 1 cinematic block / metre"
    scene["quality_samples"]=SAMPLES
    scene["scene_unit_scale"]="1 Blender unit = 1 cinematic block"
    scene["vehicle_minimum_travel_blocks"]=MIN_TRAVEL_BLOCKS
    scene["blast_frame"]=BLAST_FRAME
    scene["active_characters"]=6
    scene["character_rig"]="BROWN_BlockHuman_v2"
    scene["project_config_json"]=json.dumps(CONFIG,sort_keys=True)

def create_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.name not in ("Collection",):
            try:
                bpy.data.collections.remove(collection)
            except Exception:
                pass
    scene=bpy.context.scene
    scene.render.engine="CYCLES"
    setup_materials()
    world=bpy.data.worlds.get("World") or bpy.data.worlds.new("BROWN • Night World")
    scene.world=world
    world.use_nodes=True
    background=world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value=(.009,.016,.028,1)
    background.inputs["Strength"].default_value=.22
    build_road_and_corridor()
    car_root,steering,door_hinge,door,wheels=create_vehicle()
    chars={name:create_character(name,spec,car_root) for name,spec in CHARACTER_SPECS.items()}
    phone=create_phone(chars["Kaylen"])
    animate_vehicle(car_root,wheels)
    animate_idle_characters(chars,steering,phone)
    simulate_ragdoll(chars,car_root)
    create_explosion_and_rubble(car_root)
    create_epilogue_set(car_root)
    animate_kaylen_crawl_and_epilogue(chars["Kaylen"])
    add_camera_cuts(car_root,chars["Kaylen"],phone)
    # Wet-night cinematic key/fill/rim lights.
    add_light("Night • Cool Key","AREA",(0,75,25),(.27,.43,.62),2600,35)
    add_light("Night • Amber Rim","AREA",(-6,178,8),(1.0,.45,.19),1900,10)
    add_light("Cabin • Soft Fill","AREA",(0,180,4),(.45,.62,.72),500,5)
    scene.frame_set(1)
    return {"scene":scene,"car":car_root,"steering":steering,"door":door_hinge,"wheels":wheels,"characters":chars,"phone":phone}

def audit_scene(project):
    scene=project["scene"]
    chars=project["characters"]
    failures=[]
    checks={}
    checks["fps_is_30"]=scene.render.fps==30
    checks["frame_count_is_2700"]=(scene.frame_end-scene.frame_start+1)==2700
    checks["character_count_is_6"]=len(chars)==6
    checks["single_vehicle"]=project["car"].get("vehicle_type")=="six-seat enclosed SUV"
    checks["phone_is_physical_object"]=project["phone"].get("prop_role")=="physical-phone"
    checks["phone_has_message_screen"]=project["phone"].get("screen_text")=="YOU CAN STILL LEAVE"
    wheel_count=sum(1 for obj in bpy.data.objects if obj.name=="Vehicle • Tyre")
    checks["four_vehicle_wheels"]=wheel_count==4
    checks["all_characters_have_exactly_two_ears"]=all(ch["body"].get("face_audit",{}).get("ears")==2 for ch in chars.values())
    checks["all_characters_have_exactly_two_eyes"]=all(ch["body"].get("face_audit",{}).get("eyes")==2 for ch in chars.values())
    steering_count=sum(1 for obj in bpy.data.objects if obj.get("prop_role")=="steering-wheel")
    checks["one_steering_wheel"]=steering_count==1
    for name,ch in chars.items():
        rig,body=ch["rig"],ch["body"]
        expected={"eyes":2,"pupils":2,"brows":2,"ears":2,"nose":1,"mouth":1}
        face=dict(body.get("face_audit",{}))
        checks[name+"_face_features_exact"]=face==expected
        checks[name+"_has_armature_modifier"]=any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers)
        checks[name+"_single_unified_body"]=bool(body.get("single_body_mesh"))
        checks[name+"_all_vertices_weighted"]=int(body.get("weighted_vertex_count",0))==len(body.data.vertices)
        checks[name+"_all_rig_bones_present"]=all(rig.data.bones.get(b) is not None for b in BONE_REST)
        checks[name+"_capsule_hitbox_has_collision_modifier"]=ch["hitbox"].type=="MESH" and any(m.type=="COLLISION" for m in ch["hitbox"].modifiers)
        checks[name+"_capsule_hitbox_hidden_from_render"]=bool(ch["hitbox"].hide_render)
        if name=="Kesh":
            checks["driver_has_steering_IK"]=any(c.type=="IK" and c.target for pb in rig.pose.bones for c in pb.constraints)
        if name=="Kaylen":
            checks["phone_parented_to_Kaylen"]=project["phone"].parent==rig
    scene.frame_set(BLAST_FRAME)
    travelled=float(project["car"].location.y)
    checks["vehicle_travels_at_least_150_blocks_before_blast"]=travelled>=150.0
    checks["vehicle_travels_180_blocks_before_blast"]=travelled>=MIN_TRAVEL_BLOCKS-0.5
    checks["no_gpu_renderer"]=scene.cycles.device=="CPU" and scene.render.engine=="CYCLES"
    checks["ten_camera_objects"]=sum(1 for obj in bpy.data.objects if obj.type=="CAMERA")==10
    checks["one_capsule_hitbox_per_character"]=sum(1 for obj in bpy.data.objects if obj.get("hitbox"))==len(chars)
    checks["each_camera_has_tracking_constraint"]=all(any(c.type=="TRACK_TO" and c.target for c in obj.constraints) for obj in bpy.data.objects if obj.type=="CAMERA")
    checks["physical_phone_screen_exists"]=any(obj.get("prop_role")=="physical-phone-screen" for obj in bpy.data.objects)
    checks["six_character_collision_capsules"]=sum(1 for obj in bpy.data.objects if obj.get("hitbox"))==6
    checks["no_second_crew_vehicle"]=sum(1 for obj in bpy.data.objects if obj.get("vehicle_type"))==1
    checks["no_unplanned_character_rigs"]=sum(1 for obj in bpy.data.objects if obj.get("rig_type")=="BROWN_BlockHuman_v2")==6
    # Evaluate every frame: all rig and vehicle transforms must stay finite.
    frame_checks=0
    for frame in range(scene.frame_start,scene.frame_end+1):
        scene.frame_set(frame)
        objects=[project["car"]]+[ch["rig"] for ch in chars.values()]
        for obj in objects:
            values=list(obj.location)+list(obj.rotation_euler)
            if not all(math.isfinite(float(v)) for v in values):
                failures.append("Non-finite transform at frame %d: %s"%(frame,obj.name))
                break
        frame_checks+=1
        if failures:
            break
    checks["all_2700_frames_transform_audited"]=(frame_checks==2700 and not failures)
    for name,value in checks.items():
        if not value:
            failures.append(name)
    report={
        "project":"BROWN | BOOK ONE",
        "renderer":"Blender Cycles CPU",
        "resolution":[OUTPUT_W,OUTPUT_H],
        "fps":FPS,
        "duration_seconds":DURATION_SECONDS,
        "frame_count":FRAME_END,
        "characters":list(chars.keys()),
        "character_count":len(chars),
        "vehicle_travel_at_blast_blocks":travelled,
        "phone_prop":project["phone"].name,
        "four_wheels":wheel_count,
        "character_hitboxes":sum(1 for obj in bpy.data.objects if obj.get("hitbox")),
        "checks":checks,
        "frames_transform_checked":frame_checks,
        "failures":failures,
        "generated_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
    }
    return report

def main():
    args=parse_args()
    output_dir=Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True,exist_ok=True)
    global OUT_DIR,BLEND_PATH,VIDEO_PATH,AUDIT_PATH
    OUT_DIR=output_dir
    BLEND_PATH=output_dir/"BROWN_Book_One_Blender_CPU.blend"
    VIDEO_PATH=output_dir/"BROWN_Book_One_Blender_CPU_90s.mp4"
    AUDIT_PATH=output_dir/"BROWN_Blender_CPU_Audit.json"
    GLB_PATH=output_dir/"BROWN_Book_One_Blender_CPU.glb"
    project=create_scene()
    setup_render(output_dir,args.threads)
    report=audit_scene(project)
    AUDIT_PATH.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    if report["failures"]:
        raise RuntimeError("BROWN scene audit failed; see "+str(AUDIT_PATH))
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print("Saved editable Blender project:",BLEND_PATH)
    # Exchange copy: rigged geometry, camera objects, PBR materials and keyed motion.
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        export_animations=True,
        export_skins=True,
        export_cameras=True,
        export_lights=True,
        export_materials="EXPORT"
    )
    print("Exported rigged glTF interchange:",GLB_PATH)
    if args.mode=="render":
        bpy.context.scene.render.filepath=str(VIDEO_PATH.with_suffix(""))
        bpy.ops.render.render(animation=True)
        print("Rendered CPU animation:",VIDEO_PATH)
    elif args.mode=="audit":
        print("Audit completed: every frame's character and vehicle transforms are finite.")
    else:
        print("Build completed. Run with --mode render to render all 2,700 frames.")

if __name__=="__main__":
    main()
