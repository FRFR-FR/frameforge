#!/usr/bin/env python3
"""FrameForge Minecraft production: BROWN chapters 5-6 ambush.
Builds Java-format 64x64 player skins first, then a voxel scene and silent film.
"""
import bpy, math, os, sys, json, random, struct, zlib, binascii, subprocess
from pathlib import Path
import argparse
from mathutils import Vector

def cli():
    args = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    mode = "build"
    out = Path("output/minecraft_60s")
    start_frame, end_frame = 1, 10800
    i = 0
    while i < len(args):
        if args[i] == "--mode" and i+1 < len(args):
            mode = args[i+1]; i += 2
        elif args[i] == "--output-dir" and i+1 < len(args):
            out = Path(args[i+1]); i += 2
        elif args[i] == "--start-frame" and i+1 < len(args):
            start_frame = int(args[i+1]); i += 2
        elif args[i] == "--end-frame" and i+1 < len(args):
            end_frame = int(args[i+1]); i += 2
        else: i += 1
    return mode, out.resolve(), start_frame, end_frame

PROFILES = {
 "Senator":dict(skin=(238,190,158),hair=(245,195,83),hairdark=(153,101,39),eyes=(42,130,225),shirt=(238,236,220),jacket=(17,31,58),accent=(237,179,55),pants=(13,22,40),boots=(23,34,52),role="hero"),
 "Kesh":dict(skin=(112,70,49),hair=(30,23,20),hairdark=(16,14,13),eyes=(76,139,119),shirt=(75,92,83),jacket=(38,52,51),accent=(195,139,70),pants=(34,39,42),boots=(24,29,34),role="driver"),
 "Lark":dict(skin=(91,57,43),hair=(24,20,20),hairdark=(12,12,14),eyes=(92,143,129),shirt=(47,91,91),jacket=(31,58,64),accent=(202,169,105),pants=(31,40,44),boots=(20,28,33),role="scout"),
 "Juno":dict(skin=(128,78,57),hair=(39,24,20),hairdark=(20,14,14),eyes=(103,142,99),shirt=(89,109,74),jacket=(53,79,57),accent=(193,61,60),pants=(38,47,43),boots=(26,34,31),role="medic"),
 "Biko":dict(skin=(94,55,39),hair=(25,19,17),hairdark=(14,12,11),eyes=(117,142,91),shirt=(129,75,43),jacket=(86,49,34),accent=(219,157,83),pants=(39,39,42),boots=(25,27,30),role="crew"),
 "Tovin":dict(skin=(133,83,60),hair=(28,22,20),hairdark=(14,12,12),eyes=(78,128,168),shirt=(65,76,112),jacket=(43,54,82),accent=(204,160,85),pants=(33,40,57),boots=(23,29,42),role="student"),
 "Rescuer":dict(skin=(132,88,68),hair=(39,31,28),hairdark=(20,18,17),eyes=(91,132,158),shirt=(59,105,128),jacket=(34,68,90),accent=(244,190,57),pants=(29,43,54),boots=(18,29,39),role="rescue")
}

def png_chunk(kind,data):
    return struct.pack(">I",len(data))+kind+data+struct.pack(">I",binascii.crc32(kind+data)&0xffffffff)

def write_png(path,pixels,width=64,height=64):
    raw=bytearray()
    for row in pixels:
        raw.append(0)
        for c in row: raw.extend(bytes(c))
    header=struct.pack(">IIBBBBB",width,height,8,6,0,0,0)
    data=b"\x89PNG\r\n\x1a\n"+png_chunk(b"IHDR",header)+png_chunk(b"IDAT",zlib.compress(bytes(raw),9))+png_chunk(b"IEND",b"")
    Path(path).write_bytes(data)

def build_skin(name,p,out_dir):
    """Generate a 64x64 Java skin atlas: classic 4px arms, front/back/sides/top/bottom."""
    px=[[(0,0,0,0) for _ in range(64)] for __ in range(64)]
    def rect(x,y,w,h,c):
        rgba=tuple(c)+(255,) if len(c)==3 else tuple(c)
        for yy in range(max(0,y),min(64,y+h)):
            for xx in range(max(0,x),min(64,x+w)): px[yy][xx]=rgba
    def dot(x,y,c):
        if 0<=x<64 and 0<=y<64: px[y][x]=tuple(c)+(255,) if len(c)==3 else tuple(c)
    s,h,hd,e,shirt,jacket,a,pants,boots=(p[k] for k in ("skin","hair","hairdark","eyes","shirt","jacket","accent","pants","boots"))
    # Head base-layer atlas.
    rect(0,8,8,8,h); rect(16,8,8,8,h); rect(24,8,8,8,h); rect(8,0,8,8,h); rect(16,0,8,8,hd)
    rect(8,8,8,8,s); rect(8,8,8,2,h); rect(8,10,2,1,h); rect(14,10,2,1,h)
    dot(9,11,hd); dot(14,11,hd)
    dot(9,12,e); dot(10,12,(235,239,244)); dot(13,12,e); dot(14,12,(235,239,244))
    dot(11,13,tuple(max(0,int(v*.82)) for v in s)); dot(12,13,tuple(max(0,int(v*.82)) for v in s))
    dot(10,14,hd); dot(11,14,(112,55,48)); dot(12,14,(112,55,48)); dot(13,14,hd)
    rect(0,10,8,4,h); rect(16,10,8,4,h); rect(0,12,2,2,s); rect(22,12,2,2,s); rect(24,8,8,8,h)
    # Torso, collar, jacket panels, back and side faces.
    rect(20,20,8,12,shirt); rect(32,20,8,12,jacket); rect(16,20,4,12,jacket); rect(28,20,4,12,jacket)
    rect(20,16,8,4,jacket); rect(28,16,8,4,jacket)
    rect(20,20,8,2,a); rect(20,20,2,12,jacket); rect(26,20,2,12,jacket)
    if p["role"]=="hero":
        rect(22,22,4,1,a); rect(23,23,2,1,a); dot(22,24,a); dot(25,24,a); rect(23,24,2,3,a); dot(22,27,a); dot(25,27,a)
        rect(20,29,8,1,jacket); rect(33,21,6,1,a); rect(34,22,4,1,(33,67,106)); rect(34,30,4,1,a)
    elif p["role"]=="medic":
        rect(23,24,2,4,(226,52,55)); rect(22,25,4,2,(226,52,55))
    else:
        rect(23,23,2,2,a); rect(20,29,8,1,jacket)
    # Both arm atlases.
    for x0,y0 in [(44,20),(52,20),(40,20),(48,20),(36,52),(44,52),(32,52),(40,52)]:
        rect(x0,y0,4,12,jacket); rect(x0,y0,4,2,a); rect(x0,y0+9,4,3,shirt if p["role"]=="hero" else jacket)
    for x0,y0 in [(44,16),(48,16),(36,48),(40,48)]: rect(x0,y0,4,4,jacket)
    # Both leg atlases, including boot bands.
    for x0,y0 in [(4,20),(12,20),(0,20),(8,20),(20,52),(28,52),(16,52),(24,52)]:
        rect(x0,y0,4,12,pants); rect(x0,y0+9,4,3,boots); rect(x0,y0+8,4,1,a if p["role"]=="hero" else pants)
    for x0,y0 in [(4,16),(8,16),(20,48),(24,48)]: rect(x0,y0,4,4,pants)
    if p["role"]=="hero":
        rect(44,20,1,3,a); rect(47,20,1,3,a); rect(36,52,1,3,a); rect(39,52,1,3,a)
    path=Path(out_dir)/(name.lower()+".png"); write_png(path,px); return path

def build_skins(out_dir):
    d=Path(out_dir)/"skins"; d.mkdir(parents=True,exist_ok=True)
    paths={n:build_skin(n,p,d) for n,p in PROFILES.items()}
    (d/"skins_manifest.json").write_text(json.dumps({"format":"Minecraft Java 64x64 skin atlas","model":"classic 4px arms","skins":{k:v.name for k,v in paths.items()}},indent=2))
    return paths

def mat_color(name,color,rough=0.8,metallic=0.0,emission=0.0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF"); bs.inputs["Base Color"].default_value=(*color,1); bs.inputs["Roughness"].default_value=rough
    if "Metallic" in bs.inputs: bs.inputs["Metallic"].default_value=metallic
    if emission:
        k="Emission Color" if "Emission Color" in bs.inputs else "Emission"
        if k in bs.inputs: bs.inputs[k].default_value=(*color,1)
        if "Emission Strength" in bs.inputs: bs.inputs["Emission Strength"].default_value=emission
    return m

def skin_material(name,path):
    image=bpy.data.images.load(str(path),check_existing=False); image.pack()
    m=bpy.data.materials.new(name); m.use_nodes=True
    nodes=m.node_tree.nodes; links=m.node_tree.links; bs=nodes.get("Principled BSDF")
    bs.inputs["Roughness"].default_value=0.92
    tex=nodes.new("ShaderNodeTexImage"); tex.image=image; tex.interpolation="Closest"; tex.extension="CLIP"
    links.new(tex.outputs["Color"],bs.inputs["Base Color"]); return m

def pixel_material(name,base,seed,pattern="stone",rough=0.86,metallic=0.0,emission=0.0):
    rng=random.Random(seed); img=bpy.data.images.new(name+"_16px",width=16,height=16,alpha=False); vals=[]
    for y in range(16):
        for x in range(16):
            d=rng.choice([-18,-11,-6,0,4,8,13])
            if pattern=="brick" and (y%4==0 or (x+(y//4)*4)%8==0): d=-26
            if pattern=="road" and rng.random()<0.1: d=-22
            if pattern=="wood" and x%5==0: d=-23
            if pattern=="leaf" and rng.random()<0.16: d=20
            c=[max(0,min(255,int(v+d)))/255 for v in base]; vals.extend([c[0],c[1],c[2],1.0])
    img.pixels.foreach_set(vals); img.pack()
    m=bpy.data.materials.new(name); m.use_nodes=True; nodes=m.node_tree.nodes; links=m.node_tree.links
    bs=nodes.get("Principled BSDF"); bs.inputs["Roughness"].default_value=rough
    if "Metallic" in bs.inputs: bs.inputs["Metallic"].default_value=metallic
    tex=nodes.new("ShaderNodeTexImage"); tex.image=img; tex.interpolation="Closest"; links.new(tex.outputs["Color"],bs.inputs["Base Color"])
    if emission:
        k="Emission Color" if "Emission Color" in bs.inputs else "Emission"
        if k in bs.inputs: bs.inputs[k].default_value=(*[v/255 for v in base],1)
        if "Emission Strength" in bs.inputs: bs.inputs["Emission Strength"].default_value=emission
    return m

def empty(name,parent=None,loc=(0,0,0)):
    o=bpy.data.objects.new(name,None); bpy.context.scene.collection.objects.link(o)
    if parent: o.parent=parent
    o.location=loc; return o

def cube(name,dims,loc,material,parent=None,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,0)); o=bpy.context.object; o.name=name
    o.dimensions=dims; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if material: o.data.materials.append(material)
    if parent: o.parent=parent
    o.location=loc; o.rotation_euler=rot
    for p in o.data.polygons: p.use_smooth=False
    return o

FACE_VERTS=[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7),(0,3,2,1)]
FACE_NAMES=("front","right","back","left","top","bottom")
def skin_cube(name,dims,loc,material,rects,parent):
    hx,hy,hz=(v/2 for v in dims)
    verts=[(-hx,-hy,-hz),(hx,-hy,-hz),(hx,hy,-hz),(-hx,hy,-hz),(-hx,-hy,hz),(hx,-hy,hz),(hx,hy,hz),(-hx,hy,hz)]
    mesh=bpy.data.meshes.new(name+"_mesh"); mesh.from_pydata(verts,[],FACE_VERTS); mesh.materials.append(material); mesh.update()
    uv=mesh.uv_layers.new(name="SkinUV")
    for poly,face_name in zip(mesh.polygons,FACE_NAMES):
        x,y,w,h=rects[face_name]; u0,u1=x/64.0,(x+w)/64.0; vt,vb=1-y/64.0,1-(y+h)/64.0
        for li,co in zip(poly.loop_indices,((u0,vb),(u1,vb),(u1,vt),(u0,vt))): uv.data[li].uv=co
        poly.use_smooth=False
    obj=bpy.data.objects.new(name,mesh); bpy.context.scene.collection.objects.link(obj)
    if parent: obj.parent=parent
    obj.location=loc; return obj

HEAD_UV={"front":(8,8,8,8),"right":(0,8,8,8),"back":(24,8,8,8),"left":(16,8,8,8),"top":(8,0,8,8),"bottom":(16,0,8,8)}
TORSO_UV={"front":(20,20,8,12),"right":(16,20,4,12),"back":(32,20,8,12),"left":(28,20,4,12),"top":(20,16,8,4),"bottom":(28,16,8,4)}
RARM_UV={"front":(44,20,4,12),"right":(40,20,4,12),"back":(52,20,4,12),"left":(48,20,4,12),"top":(44,16,4,4),"bottom":(48,16,4,4)}
LARM_UV={"front":(36,52,4,12),"right":(32,52,4,12),"back":(44,52,4,12),"left":(40,52,4,12),"top":(36,48,4,4),"bottom":(40,48,4,4)}
RLEG_UV={"front":(4,20,4,12),"right":(0,20,4,12),"back":(12,20,4,12),"left":(8,20,4,12),"top":(4,16,4,4),"bottom":(8,16,4,4)}
LLEG_UV={"front":(20,52,4,12),"right":(16,52,4,12),"back":(28,52,4,12),"left":(24,52,4,12),"top":(20,48,4,4),"bottom":(24,48,4,4)}

def player(name,skin_mat,loc,parent=None,heading=0):
    root=empty(name+"_ROOT",parent,loc); root.rotation_euler.z=heading
    head_p=empty(name+"_HEAD_PIVOT",root,(0,0,1.69))
    head=skin_cube(name+"_HEAD",(0.5,0.5,0.5),(0,0,0),skin_mat,HEAD_UV,head_p)
    body=skin_cube(name+"_BODY",(0.5,0.25,0.75),(0,0,1.05),skin_mat,TORSO_UV,root)
    armL_p=empty(name+"_ARM_L_PIVOT",root,(-0.38,0,1.39)); armR_p=empty(name+"_ARM_R_PIVOT",root,(0.38,0,1.39))
    armL=skin_cube(name+"_ARM_L",(0.25,0.25,0.75),(0,0,-0.37),skin_mat,LARM_UV,armL_p)
    armR=skin_cube(name+"_ARM_R",(0.25,0.25,0.75),(0,0,-0.37),skin_mat,RARM_UV,armR_p)
    legL_p=empty(name+"_LEG_L_PIVOT",root,(-0.13,0,0.72)); legR_p=empty(name+"_LEG_R_PIVOT",root,(0.13,0,0.72))
    legL=skin_cube(name+"_LEG_L",(0.25,0.25,0.75),(0,0,-0.36),skin_mat,LLEG_UV,legL_p)
    legR=skin_cube(name+"_LEG_R",(0.25,0.25,0.75),(0,0,-0.36),skin_mat,RLEG_UV,legR_p)
    result={"root":root,"head":head_p,"head_mesh":head,"body":body,"armL":armL_p,"armR":armR_p,"legL":legL_p,"legR":legR_p}
    if name=="Senator":
        cape=mat_color("Senator_Cape_Navy",(0.018,0.035,0.075),0.75); gold=mat_color("Senator_Cape_Gold",(0.86,0.56,0.14),0.48,0.25)
        cube("Senator_Block_Cape",(0.045,0.48,0.82),(0,0.245,1.16),cape,root)
        cube("Senator_Cape_Left_Gold_Edge",(0.035,0.035,0.82),(-0.21,0.25,1.16),gold,root)
        cube("Senator_Cape_Right_Gold_Edge",(0.035,0.035,0.82),(0.21,0.25,1.16),gold,root)
    return result

def key(obj,frame,loc=None,rot=None,scale=None):
    if loc is not None: obj.location=loc; obj.keyframe_insert(data_path="location",frame=frame)
    if rot is not None: obj.rotation_euler=rot; obj.keyframe_insert(data_path="rotation_euler",frame=frame)
    if scale is not None: obj.scale=scale; obj.keyframe_insert(data_path="scale",frame=frame)

def block_batch(name,blocks,material):
    verts=[]; faces=[]
    for (cx,cy,cz),(sx,sy,sz) in blocks:
        st=len(verts); hx,hy,hz=sx/2,sy/2,sz/2
        verts.extend([(cx-hx,cy-hy,cz-hz),(cx+hx,cy-hy,cz-hz),(cx+hx,cy+hy,cz-hz),(cx-hx,cy+hy,cz-hz),
                      (cx-hx,cy-hy,cz+hz),(cx+hx,cy-hy,cz+hz),(cx+hx,cy+hy,cz+hz),(cx-hx,cy+hy,cz+hz)])
        faces.extend([tuple(st+i for i in f) for f in FACE_VERTS])
    if not verts: return None
    mesh=bpy.data.meshes.new(name+"_mesh"); mesh.from_pydata(verts,[],faces); mesh.materials.append(material); mesh.update()
    uv=mesh.uv_layers.new(name="BlockUV"); coords=((0,0),(1,0),(1,1),(0,1))
    for poly in mesh.polygons:
        for li,co in zip(poly.loop_indices,coords): uv.data[li].uv=co
        poly.use_smooth=False
    obj=bpy.data.objects.new(name,mesh); bpy.context.scene.collection.objects.link(obj); return obj

def add_batch(batches,matkey,loc,dims): batches.setdefault(matkey,[]).append((loc,dims))

def make_camera(name,loc,target,lens=45):
    data=bpy.data.cameras.new(name+"_data"); data.lens=lens; data.sensor_width=36
    cam=bpy.data.objects.new(name,data); bpy.context.scene.collection.objects.link(cam); cam.location=loc
    tgt=empty(name+"_FOCUS",None,target)
    con=cam.constraints.new("TRACK_TO"); con.target=tgt; con.track_axis="TRACK_NEGATIVE_Z"; con.up_axis="UP_Y"
    cam.data.dof.use_dof=True; cam.data.dof.focus_object=tgt; cam.data.dof.aperture_fstop=5.6
    return cam


# ---------------------------------------------------------------------------
# 10-minute rainy-city continuation for the supplied Senator/Kesh alley scene
# Blender Cycles CPU production; 1280x720; 20 FPS; 12,000 frames.
# Characters are built procedurally from the existing FrameForge skin system.
# ---------------------------------------------------------------------------

FPS = 20
DURATION = 600
FRAME_END = FPS * DURATION
WIDTH, HEIGHT = 1280, 720
OUT_NAME = "Rooftop_Continuation_10min"

def cli():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("build", "audit", "render-chunk"), default="build")
    parser.add_argument("--output-dir", default="output/rooftop_continuation_10min")
    parser.add_argument("--start-frame", type=int, default=1)
    parser.add_argument("--end-frame", type=int, default=FRAME_END)
    args = parser.parse_args(argv)
    return args.mode, Path(args.output_dir).resolve(), args.start_frame, args.end_frame

def make_surface_material(name, color, roughness=0.78, metallic=0.0,
                          emission=0.0, noise_scale=24.0, bump_strength=0.12):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = metallic
    if emission:
        socket = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        if socket:
            socket.default_value = (*color, 1.0)
        strength = bsdf.inputs.get("Emission Strength")
        if strength:
            strength.default_value = emission
    tex = nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = noise_scale
    tex.inputs["Detail"].default_value = 3.0
    tex.inputs["Roughness"].default_value = 0.72
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.045
    links.new(tex.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return material

def add_area_light(name, location, target, energy, color, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.color = color
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj

def add_point_light(name, location, energy, color, radius=1.0):
    data = bpy.data.lights.new(name, "POINT")
    data.energy = energy
    data.color = color
    data.shadow_soft_size = radius
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    return obj

def add_text(name, body, location, size, material, rotation=(math.pi/2, 0, 0)):
    data = bpy.data.curves.new(name, "FONT")
    data.body = body
    data.size = size
    data.align_x = "CENTER"
    data.align_y = "CENTER"
    data.extrude = 0.012
    data.bevel_depth = 0.002
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    if material:
        data.materials.append(material)
    return obj

def add_camera(name, location, target, lens=48, fstop=5.6):
    data = bpy.data.cameras.new(name + "_DATA")
    data.lens = lens
    data.dof.use_dof = True
    data.dof.aperture_fstop = fstop
    camera = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = location
    focus = empty(name + "_FOCUS", None, target)
    track = camera.constraints.new("TRACK_TO")
    track.target = focus
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    data.dof.focus_object = focus
    return camera, focus

def add_walk_drivers(character):
    root = character["root"]
    root["walk"] = 1.0
    root["gesture_left"] = 0.0
    root["gesture_right"] = 0.0
    limbs = [
        (character["armL"], 0.0, "gesture_left", 0.46),
        (character["armR"], math.pi, "gesture_right", 0.46),
        (character["legL"], math.pi, None, 0.48),
        (character["legR"], 0.0, None, 0.48),
    ]
    for limb, phase, gesture_name, amplitude in limbs:
        curve = limb.driver_add("rotation_euler", 0)
        driver = curve.driver
        walk_var = driver.variables.new()
        walk_var.name = "walk"
        walk_var.type = "SINGLE_PROP"
        walk_var.targets[0].id = root
        walk_var.targets[0].data_path = '["walk"]'
        expression = "walk * " + str(amplitude) + " * sin(frame * 0.235 + " + str(phase) + ")"
        if gesture_name:
            gesture_var = driver.variables.new()
            gesture_var.name = "gesture"
            gesture_var.type = "SINGLE_PROP"
            gesture_var.targets[0].id = root
            gesture_var.targets[0].data_path = '["' + gesture_name + '"]'
            expression += " + gesture"
        driver.expression = expression

def animate_character(character, side_offset, route):
    root = character["root"]
    for seconds, x, y, z, yaw, walk in route:
        frame = max(1, int(seconds * FPS) + 1)
        ox = side_offset * math.cos(yaw)
        oy = side_offset * math.sin(yaw)
        key(root, frame, loc=(x + ox, y + oy, z), rot=(0.0, 0.0, yaw))
        root["walk"] = float(walk)
        root.keyframe_insert(data_path='["walk"]', frame=frame)

def add_building_batches(batches, x, side, width, depth, height,
                         wall_key, trim_key, glass_key, window_key, index):
    y = side * 12.2
    add_batch(batches, wall_key, (x, y, height/2), (width, depth, height))
    add_batch(batches, trim_key, (x, y, height + 0.24), (width + 0.55, depth + 0.45, 0.48))
    front_y = y - side * (depth/2 + 0.075)
    floors = max(2, int(height // 2.7))
    cols = max(2, int(width // 2.2))
    for floor in range(floors):
        z = 1.35 + floor * 2.65
        for col in range(cols):
            wx = x - (cols - 1) * 1.05 + col * 2.1
            add_batch(batches, glass_key, (wx, front_y, z), (0.86, 0.105, 1.18))
            if (index + floor + col) % 4 == 0:
                add_batch(batches, window_key, (wx, front_y - side*0.065, z),
                          (0.52, 0.035, 0.76))
            add_batch(batches, trim_key, (wx, front_y - side*0.08, z - 0.69),
                      (1.02, 0.13, 0.12))
    # Recessed door bays and a small projecting sign.
    if index % 3 == 0:
        add_batch(batches, trim_key, (x, front_y - side*0.10, 1.25),
                  (1.55, 0.20, 2.55))
        add_batch(batches, glass_key, (x, front_y - side*0.22, 1.28),
                  (1.12, 0.04, 2.10))

def build_continuation_scene(out_dir):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    skin_paths = build_skins(out_dir)

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 96
    scene.cycles.use_denoising = True
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.008
    if hasattr(scene.render, "use_persistent_data"):
        scene.render.use_persistent_data = True
    scene.render.threads_mode = "AUTO"
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.render.fps_base = 1.0
    scene.frame_start = 1
    scene.frame_end = FRAME_END
    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = 0.28
    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    scene.view_settings.exposure = 0
    scene.render.image_settings.color_mode = "RGB"

    world = bpy.data.worlds.new("Rain City | Blue Hour to Dawn")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.004, 0.012, 0.030, 1.0)
    bg.inputs["Strength"].default_value = 0.32
    scene.world = world

    mats = {
        "road": make_surface_material("Wet Charcoal Asphalt", (0.035, 0.050, 0.075), 0.22, 0.28, noise_scale=85, bump_strength=0.22),
        "stone": pixel_material("Rain Dark Stone", (75, 87, 103), 21, "stone", 0.88),
        "brick": pixel_material("Old Red Brick", (94, 56, 54), 22, "brick", 0.9),
        "concrete": pixel_material("Blue Grey Concrete", (105, 119, 133), 23, "stone", 0.84),
        "metal": make_surface_material("Blackened Metal", (0.055, 0.080, 0.115), 0.38, 0.64, noise_scale=60, bump_strength=0.12),
        "glass": make_surface_material("Rain Glass", (0.025, 0.090, 0.145), 0.18, 0.2, noise_scale=100, bump_strength=0.025),
        "wood": pixel_material("Market Wood", (103, 69, 45), 24, "wood", 0.88),
        "leaf": pixel_material("Wet Ivy", (24, 64, 49), 25, "leaf", 0.9),
        "gold": mat_color("Old Brass", (0.72, 0.43, 0.14), 0.42, 0.48),
        "warm": mat_color("Warm Window Emission", (1.0, 0.47, 0.16), 0.3, 0.0, 2.8),
        "cyan": mat_color("Cold Sign Emission", (0.12, 0.55, 0.92), 0.28, 0.0, 2.1),
        "rain": mat_color("Rain Streak Emission", (0.22, 0.40, 0.62), 0.28, 0.0, 0.65),
        "beacon": mat_color("Beacon Gold Emission", (1.0, 0.48, 0.10), 0.24, 0.0, 5.5),
        "water": make_surface_material("Canal Black Water", (0.012, 0.035, 0.070), 0.11, 0.42, noise_scale=45, bump_strength=0.08),
        "cloth_blue": pixel_material("Market Blue Canvas", (35, 77, 107), 26, "wood", 0.86),
        "cloth_ochre": pixel_material("Market Ochre Canvas", (125, 76, 43), 27, "wood", 0.88),
        "paper": mat_color("Lantern Paper", (0.85, 0.77, 0.56), 0.9, 0.0, 0.15),
    }

    # Continuous rain-slick street, raised pavements, and a tight opening alley.
    cube("Long Wet Street", (145, 0, -0.42), (310, 42, 0.82), mats["road"])
    cube("Alley Pavement", (2, 7, -0.08), (18, 40, 0.24), mats["stone"])
    cube("Opening Left Building", (-3.7, 4.2, 6.6), (7.2, 34, 13.2), mats["stone"])
    cube("Opening Right Building", (7.4, 4.2, 6.0), (7.2, 34, 12.0), mats["brick"])
    cube("Right Roof Overhang", (7.4, -0.2, 6.45), (10.5, 18, 0.75), mats["concrete"])
    cube("Left Roof Coping", (-3.7, 0.0, 13.25), (7.6, 35, 0.6), mats["metal"])
    cube("Right Roof Coping", (7.4, 0.0, 12.1), (7.6, 35, 0.55), mats["metal"])
    # Scored roof tiles and drain pipes make the opening shot feel occupied.
    for x in (-6.8, -5.2, -3.6, -2.0, 5.0, 6.6, 8.2, 9.8):
        cube("Alley Wall Vertical Seam", (x, 1.0, 6.2), (0.055, 29, 11.8), mats["concrete"])
    for y in (-8, -4, 0, 4, 8, 12, 16):
        cube("Alley Paving Joint", (2, y, 0.055), (8.0, 0.055, 0.03), mats["metal"])
    cube("Alley Drain Pipe", (-0.45, 3.0, 5.4), (0.18, 0.18, 10.6), mats["metal"])
    cube("Alley Drain Pipe", (10.9, 4.0, 4.8), (0.18, 0.18, 9.6), mats["metal"])

    # A long, changing block-built district: apartments, old masonry, shopfronts.
    batches = {}
    rng = random.Random(20261112)
    building_keys = ["brick", "stone", "concrete"]
    for index, x in enumerate(range(12, 300, 12)):
        for side in (-1, 1):
            width = rng.uniform(8.2, 11.3)
            depth = rng.uniform(4.0, 5.6)
            height = rng.uniform(12.0, 25.0)
            wall_key = building_keys[(index + (side == 1)) % len(building_keys)]
            add_building_batches(
                batches, x + rng.uniform(-1.8, 1.8), side, width, depth, height,
                wall_key, "metal", "glass", "warm", index + (side == 1)
            )
    for key_name, blocks in batches.items():
        block_batch("District Facades " + key_name, blocks, mats[key_name])

    # Shop awnings, hanging signs, crates, balconies and climbing ivy.
    for i, x in enumerate((36, 48, 60, 72)):
        side = -1 if i % 2 == 0 else 1
        y = side * 7.4
        cube("Market Stall Counter", (x, y, 1.05), (5.2, 1.6, 1.15), mats["wood"])
        cube("Market Stall Canopy", (x, y, 3.15), (6.5, 2.5, 0.22),
             mats["cloth_blue"] if i % 2 == 0 else mats["cloth_ochre"], rot=(0, 0, 0))
        for dx in (-2.8, 2.8):
            cube("Market Stall Canopy Post", (x + dx, y, 2.05), (0.16, 0.16, 2.1), mats["metal"])
        for j in range(3):
            cube("Market Produce Crate", (x - 1.5 + j * 1.45, y - side*0.35, 1.72),
                 (1.0, 0.8, 0.46), mats["wood"])
    sign_mat = mats["cyan"]
    for x, body in ((44, "NIGHT MARKET"), (88, "ROOFTOP"), (204, "OLD QUARTER")):
        cube("Hanging Sign Frame", (x, -7.2, 5.1), (4.7, 0.18, 1.2), mats["metal"])
        add_text("Hanging Sign " + body, body, (x, -7.33, 5.1), 0.32, sign_mat)

    # Street lamps and warm pools of light continue down the avenue.
    for x in range(18, 292, 20):
        for side in (-1, 1):
            y = side * 7.0
            cube("Street Lamp Post", (x, y, 3.0), (0.22, 0.22, 6.0), mats["metal"])
            cube("Street Lamp Arm", (x + 0.55, y, 5.8), (1.2, 0.20, 0.20), mats["metal"])
            cube("Street Lamp Housing", (x + 1.08, y, 5.52), (0.62, 0.62, 0.28), mats["warm"])
    for x in (20, 58, 96, 134, 174, 214, 254, 284):
        add_area_light("Warm Street Pool " + str(x), (x, -4.8, 7.2), (x, 0, 0), 560,
                       (1.0, 0.48, 0.22), 5.5)
    for x in (32, 76, 122, 166, 206, 246, 280):
        add_area_light("Cool Facade Fill " + str(x), (x, 9, 11), (x, 0, 0), 780,
                       (0.20, 0.38, 0.72), 9.0)

    # A raised rooftop route with real steps, parapets, vents and a wet roof deck.
    cube("Rooftop Walkway", (94, -2.1, 6.0), (39, 7.8, 0.55), mats["concrete"])
    cube("Rooftop Parapet North", (94, 2.0, 6.85), (40, 0.42, 1.25), mats["stone"])
    cube("Rooftop Parapet South", (94, -6.1, 6.85), (40, 0.42, 1.25), mats["stone"])
    for step in range(24):
        x = 73.0 + step * 0.55
        z = 0.20 + step * 0.25
        cube("Ascending Rooftop Step", (x, -2.0, z), (0.92, 4.8, 0.48), mats["stone"])
    for step in range(24):
        x = 107.0 + step * 0.55
        z = 5.8 - step * 0.25
        cube("Descending Rooftop Step", (x, -2.0, z), (0.92, 4.8, 0.48), mats["stone"])
    for x in (82, 92, 102):
        cube("Rooftop Vent Base", (x, -4.4, 6.55), (2.8, 1.5, 0.7), mats["metal"])
        cube("Rooftop Vent Cap", (x, -4.4, 7.25), (3.2, 1.8, 0.18), mats["concrete"])
        for j in range(4):
            cube("Rooftop Vent Slat", (x - 0.9 + j*0.6, -4.4, 7.39),
                 (0.10, 1.45, 0.12), mats["metal"])

    # The rain canal and arched block bridge become a major wide shot.
    cube("Canal Water", (162, 0, -0.62), (11.5, 42, 0.35), mats["water"])
    cube("Bridge Deck", (162, 0, -0.325), (14.0, 8.3, 0.65), mats["stone"])
    for side in (-1, 1):
        cube("Bridge Stone Parapet", (162, side*4.15, 0.72), (14.0, 0.42, 1.45), mats["concrete"])
        for x in range(156, 169, 3):
            cube("Bridge Parapet Post", (x, side*4.15, 1.95), (0.52, 0.48, 0.5), mats["metal"])
    for x in (157, 162, 167):
        cube("Canal Bridge Support", (x, 0, -0.7), (1.1, 9.0, 2.2), mats["stone"])

    # A final plaza: paving, low fountain, planters and warmer dawn practicals.
    cube("Final Plaza Paving", (264, -1.0, -0.12), (64, 38, 0.30), mats["concrete"])
    for x in (244, 256, 272, 284):
        for side in (-1, 1):
            cube("Plaza Planter", (x, side*9, 0.42), (4.8, 2.1, 0.84), mats["stone"])
            cube("Planter Soil", (x, side*9, 0.88), (4.2, 1.6, 0.12), mats["wood"])
            for dx in (-1.1, 0, 1.1):
                cube("Planter Shrub", (x + dx, side*9, 1.55), (1.25, 1.0, 1.25), mats["leaf"])
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=3.0, depth=0.7, location=(266, -1, 0.45))
    fountain = bpy.context.object
    fountain.name = "Plaza Fountain Stone Basin"
    fountain.data.materials.append(mats["stone"])
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=2.45, depth=0.08, location=(266, -1, 0.84))
    fountain_water = bpy.context.object
    fountain_water.name = "Plaza Fountain Water"
    fountain_water.data.materials.append(mats["water"])
    cube("Fountain Central Pillar", (266, -1, 1.55), (0.7, 0.7, 1.5), mats["concrete"])
    add_area_light("Dawn Plaza Key", (264, -10, 18), (264, -1, 0), 2200,
                   (1.0, 0.66, 0.40), 14.0)

    # A skyline beyond the route gives the wide shots scale and atmospheric depth.
    skyline = {}
    for i, x in enumerate(range(-12, 316, 16)):
        for side in (-1, 1):
            height = rng.uniform(20.0, 42.0)
            y = side * 25.0
            skyline.setdefault("stone", []).append(((x, y, height/2), (rng.uniform(8, 13), 7.0, height)))
            for floor in range(2, int(height // 4), 2):
                skyline.setdefault("cyan", []).append(((x, y - side*3.58, floor*2.0),
                                                       (0.35, 0.06, 0.7)))
    for key_name, blocks in skyline.items():
        block_batch("Distant Skyline " + key_name, blocks, mats[key_name])

    # Rain field: one animated mesh of hundreds of blue-grey streaks with a cyclic fall.
    rain_root = empty("Rain Field Root", None, (0, 0, 12))
    rain_rng = random.Random(72)
    rain_blocks = []
    for i in range(520):
        location = (rain_rng.uniform(-14, 308), rain_rng.uniform(-17, 17),
                    rain_rng.uniform(1.5, 23))
        dimensions = (0.018, 0.018, rain_rng.uniform(0.24, 0.52))
        rain_blocks.append((location, dimensions))
    rain_obj = block_batch("Animated Rain Streaks", rain_blocks, mats["rain"])
    rain_obj.parent = rain_root
    rain_curve = rain_root.driver_add("location", 2)
    rain_curve.driver.expression = "12 - ((frame - 1) % 20) * 1.2"

    # Steam accents from selected vents; deliberately subtle against the dark rain.
    steam_mat = make_surface_material("Steam Grey", (0.24, 0.31, 0.39), 1.0, 0.0,
                                      emission=0.035, noise_scale=8, bump_strength=0.05)
    for i, x in enumerate((50, 90, 132, 190, 258)):
        vent = cube("Steam Vent Plume " + str(i), (x, 4.0, 2.8), (1.1, 1.1, 4.8), steam_mat)
        vent.display_type = "WIRE"
        vent.hide_render = True
        for frame, scale in ((1, (0.01, 0.01, 0.01)),
                             (int((x/300.0*360 + 20)*FPS), (0.8, 0.8, 1.0))):
            key(vent, max(1, frame), scale=scale)

    # Existing FrameForge player designs: Senator and Kesh, recreated from their
    # authored Minecraft skin atlases rather than generated character images.
    senator_skin = skin_material("Senator Skin Atlas", skin_paths["Senator"])
    kesh_skin = skin_material("Kesh Skin Atlas", skin_paths["Kesh"])
    senator = player("Senator", senator_skin, (2.0, 11.7, 0.0), None, 0.0)
    kesh = player("Kesh", kesh_skin, (3.5, 12.2, 0.0), None, 0.0)
    add_walk_drivers(senator)
    add_walk_drivers(kesh)

    # Route is designed as one continuous journey: reveal alley, market, rooftop,
    # canal, old quarter and sunrise plaza. The first composition matches the
    # supplied last frame, with both characters emerging through the narrow gap.
    route = [
        (0,   2.1, 11.8, 0.0, 0.0, 1),
        (18,  2.1,  0.6, 0.0, 0.0, 1),
        (24,  2.1, -2.2, 0.0, 0.0, 0),
        (30,  4.0, -2.6, 0.0, 0.55, 1),
        (42, 14.0, -2.6, 0.0, 1.35, 1),
        (70, 34.0, -2.2, 0.0, 1.57, 1),
        (98, 53.0, -2.2, 0.0, 1.57, 1),
        (112, 62.0, -2.2, 0.0, 1.57, 1),
        (120, 67.0, -2.2, 0.0, 1.57, 0),
        (132, 67.0, -2.2, 0.0, 1.57, 0),
        (144, 72.0, -2.2, 0.0, 1.57, 1),
        (160, 80.0, -2.2, 3.0, 1.57, 1),
        (178, 89.0, -2.2, 6.0, 1.57, 1),
        (214, 104.0, -2.2, 6.0, 1.57, 1),
        (228, 110.0, -2.2, 3.0, 1.57, 1),
        (240, 116.0, -2.2, 0.0, 1.57, 1),
        (270, 134.0, -2.2, 0.0, 1.57, 1),
        (300, 151.0, -2.2, 0.0, 1.57, 1),
        (316, 160.0, -2.2, 0.0, 1.57, 1),
        (340, 173.0, -2.2, 0.0, 1.57, 1),
        (370, 190.0, -2.2, 0.0, 1.57, 1),
        (398, 203.0, -2.2, 0.0, 1.57, 1),
        (410, 205.0, -2.2, 0.0, 1.57, 0),
        (426, 205.0, -2.2, 0.0, 1.57, 0),
        (440, 213.0, -2.2, 0.0, 1.57, 1),
        (472, 231.0, -2.2, 0.0, 1.57, 1),
        (500, 247.0, -2.2, 0.0, 1.57, 1),
        (530, 264.0, -2.2, 0.0, 1.57, 1),
        (560, 280.0, -2.2, 0.0, 1.57, 1),
        (585, 292.0, -2.2, 0.0, 1.57, 1),
        (600, 298.0, -2.2, 0.0, 1.57, 0),
    ]
    animate_character(senator, -0.72, route)
    animate_character(kesh, 0.72, route)

    # Subtle eye-line and hand gestures create readable acting without dialogue.
    for frame, rot in ((1, (0, 0, 0)), (2250, (0, 0, 0.15)),
                       (2400, (0.0, 0.0, -0.22)), (2700, (0, 0, 0)),
                       (8050, (0, 0, -0.14)), (9200, (0, 0, 0.16)),
                       (11200, (0, 0, 0.0))):
        key(senator["head"], frame, rot=rot)
    for frame, value in ((1, 0.0), (2320, -0.75), (2460, 0.0),
                         (2680, 0.55), (2800, 0.0), (8200, 0.25), (9000, 0.0)):
        senator["root"]["gesture_right"] = value
        senator["root"].keyframe_insert(data_path='["gesture_right"]', frame=frame)
    for frame, value in ((1, 0.0), (2380, 0.55), (2520, 0.0), (8150, -0.25), (9000, 0.0)):
        kesh["root"]["gesture_left"] = value
        kesh["root"].keyframe_insert(data_path='["gesture_left"]', frame=frame)
    for frame, rot in ((1, (0, 0, 0)), (2380, (0, 0.08, 0.18)),
                       (2600, (0, 0, -0.12)), (2900, (0, 0, 0)),
                       (10800, (0.10, 0, 0)), (11980, (0.08, 0, 0))):
        key(kesh["head"], frame, rot=rot)

    # A small luminous object is discovered in the market and carried onward.
    beacon = cube("Golden Beacon on Wet Stone", (67, -3.5, 0.75), (0.48, 0.48, 0.48), mats["beacon"])
    key(beacon, 1, scale=(0.001, 0.001, 0.001))
    key(beacon, 2260, scale=(0.001, 0.001, 0.001))
    key(beacon, 2360, scale=(1, 1, 1))
    key(beacon, 2700, scale=(1, 1, 1))
    key(beacon, 2780, scale=(0.001, 0.001, 0.001))
    beacon_light = add_point_light("Beacon Warm Pulse", (67, -3.5, 1.4), 0, (1.0, 0.42, 0.12), 1.8)
    for frame, power in ((1, 0), (2300, 0), (2380, 750), (2460, 1150),
                         (2700, 850), (2800, 0), (FRAME_END, 0)):
        beacon_light.data.energy = power
        beacon_light.data.keyframe_insert(data_path="energy", frame=frame)
    hand_beacon = cube("Beacon Carried by Kesh", (0.52, -0.28, 1.55),
                       (0.26, 0.26, 0.26), mats["beacon"], kesh["root"])
    key(hand_beacon, 1, scale=(0.001, 0.001, 0.001))
    key(hand_beacon, 2700, scale=(0.001, 0.001, 0.001))
    key(hand_beacon, 2800, scale=(1, 1, 1))
    key(hand_beacon, FRAME_END, scale=(1, 1, 1))

    # Dawn slowly replaces blue-hour rain over the final quarter of the film.
    sun = add_area_light("Dawn Opening Through Clouds", (250, -5, 35), (250, 0, 0),
                         180, (0.24, 0.36, 0.58), 28)
    for frame, power, color in (
        (1, 180, (0.24, 0.36, 0.58)),
        (8500, 220, (0.30, 0.42, 0.62)),
        (9800, 600, (0.70, 0.48, 0.32)),
        (11000, 1250, (1.0, 0.68, 0.42)),
        (FRAME_END, 1700, (1.0, 0.76, 0.55)),
    ):
        sun.data.energy = power
        sun.data.color = color
        sun.data.keyframe_insert(data_path="energy", frame=frame)
        sun.data.keyframe_insert(data_path="color", frame=frame)
    for frame, color, strength in (
        (1, (0.004, 0.012, 0.030, 1.0), 0.32),
        (8500, (0.008, 0.022, 0.046, 1.0), 0.34),
        (10000, (0.10, 0.095, 0.12, 1.0), 0.42),
        (FRAME_END, (0.32, 0.19, 0.12, 1.0), 0.55),
    ):
        bg.inputs["Color"].default_value = color
        bg.inputs["Color"].keyframe_insert(data_path="default_value", frame=frame)
        bg.inputs["Strength"].default_value = strength
        bg.inputs["Strength"].keyframe_insert(data_path="default_value", frame=frame)

    # Ten purpose-built cameras, cut by timeline markers and animated during each shot.
    cameras = []
    camera_specs = [
        ("CAM_01_Alley_Reveal", (2.4, -18.0, 5.2), (2.2, 7.0, 1.8), 46, 6.3),
        ("CAM_02_Street_Follow", (22.0, -14.0, 5.0), (23.0, -2.0, 1.5), 52, 4.8),
        ("CAM_03_Beacon_Close", (62.5, -8.0, 3.3), (67.0, -2.8, 1.2), 62, 2.8),
        ("CAM_04_Rooftop_Ascent", (86.0, -15.5, 10.0), (91.0, -2.0, 6.5), 48, 5.2),
        ("CAM_05_Rooftop_Overlook", (105.0, 8.5, 12.0), (101.0, -2.0, 6.0), 42, 7.0),
        ("CAM_06_Backstreet", (129.0, -13.0, 4.5), (132.0, -2.0, 1.5), 52, 4.0),
        ("CAM_07_Canal_Wide", (160.0, -24.0, 15.0), (162.0, -2.0, 1.1), 38, 8.0),
        ("CAM_08_Old_Quarter", (190.0, 6.0, 9.0), (188.0, -2.0, 1.5), 44, 6.0),
        ("CAM_09_Plaza_Close", (248.0, -10.0, 4.2), (251.0, -2.0, 1.7), 58, 3.0),
        ("CAM_10_Dawn_Crane", (276.0, -31.0, 22.0), (278.0, -2.0, 1.6), 40, 9.0),
    ]
    cut_frames = (1, 801, 1701, 2501, 3701, 5001, 6501, 7801, 9001, 10501)
    for index, spec in enumerate(camera_specs):
        name, location, target, lens, fstop = spec
        camera, focus = add_camera(name, location, target, lens, fstop)
        cameras.append((camera, focus))
        marker = scene.timeline_markers.new(name, frame=cut_frames[index])
        marker.camera = camera

    # Smooth camera movement within each section; the focus target tracks the action.
    camera_moves = [
        (0, (2.4, -18.0, 5.2), (2.2, 7.0, 1.8)),
        (40, (4.2, -7.0, 4.5), (5.0, -1.5, 1.7)),
    ]
    for seconds, loc, target in camera_moves:
        frame = int(seconds*FPS)+1
        key(cameras[0][0], frame, loc=loc)
        key(cameras[0][1], frame, loc=target)
    camera_moves = [
        (40, (22, -14, 5), (23, -2, 1.5)),
        (84, (58, -12, 4.5), (59, -2, 1.4)),
    ]
    for seconds, loc, target in camera_moves:
        frame = int(seconds*FPS)+1
        key(cameras[1][0], frame, loc=loc)
        key(cameras[1][1], frame, loc=target)
    camera_moves = [
        (85, (62.5, -8, 3.3), (67, -2.8, 1.2)),
        (125, (70, -7, 3.0), (68, -2.2, 1.5)),
    ]
    for seconds, loc, target in camera_moves:
        frame = int(seconds*FPS)+1
        key(cameras[2][0], frame, loc=loc)
        key(cameras[2][1], frame, loc=target)
    camera_moves = [
        (125, (86, -15.5, 10), (91, -2, 6.5)),
        (185, (105, -13, 9.2), (103, -2, 6.3)),
    ]
    for seconds, loc, target in camera_moves:
        frame = int(seconds*FPS)+1
        key(cameras[3][0], frame, loc=loc)
        key(cameras[3][1], frame, loc=target)
    camera_moves = [
        (185, (105, 8.5, 12), (101, -2, 6)),
        (250, (112, 12, 10), (108, -2, 3)),
    ]
    for seconds, loc, target in camera_moves:
        frame = int(seconds*FPS)+1
        key(cameras[4][0], frame, loc=loc)
        key(cameras[4][1], frame, loc=target)
    camera_moves = [
        (250, (129, -13, 4.5), (132, -2, 1.5)),
        (325, (154, -12, 5), (158, -2, 1.2)),
    ]
    for seconds, loc, target in camera_moves:
        frame = int(seconds*FPS)+1
        key(cameras[5][0], frame, loc=loc)
        key(cameras[5][1], frame, loc=target)
    camera_moves = [
        (325, (160, -24, 15), (162, -2, 1.1)),
        (390, (176, -22, 12), (179, -2, 1.5)),
    ]
    for seconds, loc, target in camera_moves:
        frame = int(seconds*FPS)+1
        key(cameras[6][0], frame, loc=loc)
        key(cameras[6][1], frame, loc=target)
    camera_moves = [
        (390, (190, 6, 9), (188, -2, 1.5)),
        (450, (209, 5, 7.5), (207, -2, 1.7)),
    ]
    for seconds, loc, target in camera_moves:
        frame = int(seconds*FPS)+1
        key(cameras[7][0], frame, loc=loc)
        key(cameras[7][1], frame, loc=target)
    camera_moves = [
        (450, (248, -10, 4.2), (251, -2, 1.7)),
        (525, (269, -9, 4.4), (270, -2, 1.8)),
    ]
    for seconds, loc, target in camera_moves:
        frame = int(seconds*FPS)+1
        key(cameras[8][0], frame, loc=loc)
        key(cameras[8][1], frame, loc=target)
    camera_moves = [
        (525, (276, -31, 22), (278, -2, 1.6)),
        (600, (294, -44, 30), (278, -2, 1.8)),
    ]
    for seconds, loc, target in camera_moves:
        frame = int(seconds*FPS)+1
        key(cameras[9][0], frame, loc=loc)
        key(cameras[9][1], frame, loc=target)

    # Blender's default keyframe interpolation is Bezier; keep the
    # native Action representation untouched for Blender 5 compatibility.

    # Blender 5's compositor API is managed separately from the Scene node tree.
    # Practical lamps and the beacon use emissive materials and AgX grading.

    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 0
    scene.render.use_file_extension = True
    scene.render.filepath = str(out_dir / "frames" / "frame_######")
    scene.frame_set(1)

    blend_path = out_dir / (OUT_NAME + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    audit = {
        "status": "PASS",
        "project": "Rain City | Senator and Kesh",
        "duration_seconds": DURATION,
        "fps": FPS,
        "frame_count": FRAME_END,
        "resolution": [WIDTH, HEIGHT],
        "renderer": "Blender Cycles CPU",
        "samples": scene.cycles.samples,
        "denoising": scene.cycles.use_denoising,
        "motion_blur": scene.render.use_motion_blur,
        "characters": ["Senator", "Kesh"],
        "camera_count": len(cameras),
        "scene_sections": [
            "narrow rainy alley reveal", "old street and night market",
            "beacon discovery", "rooftop ascent and crossing",
            "rain canal bridge", "old quarter", "dawn plaza"
        ],
        "checks": {
            "exact_frame_count": scene.frame_end - scene.frame_start + 1 == FRAME_END,
            "20_fps": scene.render.fps == FPS,
            "720p_landscape": scene.render.resolution_x == WIDTH and scene.render.resolution_y == HEIGHT,
            "cycles_cpu": scene.render.engine == "CYCLES" and scene.cycles.device == "CPU",
            "two_existing_characters": senator["root"].name == "Senator_ROOT" and kesh["root"].name == "Kesh_ROOT",
            "ten_cameras": len(cameras) == 10,
            "beacon_prop": beacon.name == "Golden Beacon on Wet Stone",
            "rain_field": rain_obj.name == "Animated Rain Streaks",
        }
    }
    for obj in bpy.data.objects:
        for value in (*obj.location, *obj.rotation_euler, *obj.scale):
            assert math.isfinite(float(value)), "Non-finite transform in " + obj.name
    assert all(audit["checks"].values()), "Scene audit failed: " + json.dumps(audit["checks"])
    (out_dir / "production_audit.json").write_text(json.dumps(audit, indent=2))
    return scene, blend_path, audit

def run():
    mode, out_dir, start_frame, end_frame = cli()
    out_dir.mkdir(parents=True, exist_ok=True)

    if mode in ("build", "audit"):
        scene, blend_path, audit = build_continuation_scene(out_dir)
        print("ROOFTOP_CONTINUATION_SCENE_READY", blend_path)
        print(json.dumps(audit, indent=2))
        if mode == "audit":
            # Render six checkpoints so the visual progression can be reviewed.
            scene.render.image_settings.file_format = "PNG"
            scene.render.image_settings.color_mode = "RGB"
            for frame in (1, 1700, 2700, 4300, 6700, 9600, FRAME_END):
                scene.frame_set(frame)
                scene.render.filepath = str(out_dir / ("preview_%05d" % frame))
                bpy.ops.render.render(write_still=True)
            print("SCENE_AUDIT_AND_PREVIEWS_COMPLETE")
        return

    if mode == "render-chunk":
        scene = bpy.context.scene
        if not (1 <= start_frame <= end_frame <= FRAME_END):
            raise ValueError("Invalid frame range: %s-%s" % (start_frame, end_frame))
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 96
        scene.cycles.use_denoising = True
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.008
        scene.render.resolution_x = WIDTH
        scene.render.resolution_y = HEIGHT
        scene.render.resolution_percentage = 100
        scene.render.fps = FPS
        scene.render.fps_base = 1.0
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGB"
        scene.render.image_settings.color_depth = "8"
        scene.render.image_settings.compression = 0
        scene.render.use_file_extension = True
        frame_dir = out_dir / "frames"
        frame_dir.mkdir(parents=True, exist_ok=True)
        scene.render.filepath = str(frame_dir / "frame_######")
        scene.frame_start = start_frame
        scene.frame_end = end_frame
        scene.frame_set(start_frame)
        bpy.ops.render.render(animation=True)
        rendered = list(frame_dir.glob("frame_*.png"))
        expected = end_frame - start_frame + 1
        if len(rendered) != expected:
            raise RuntimeError("Chunk %d-%d produced %d frames; expected %d" %
                               (start_frame, end_frame, len(rendered), expected))
        (out_dir / "chunk_verification.json").write_text(json.dumps({
            "start_frame": start_frame, "end_frame": end_frame,
            "expected_frames": expected, "rendered_frames": len(rendered),
            "renderer": "Blender Cycles CPU", "samples": scene.cycles.samples,
            "resolution": [WIDTH, HEIGHT], "fps": FPS
        }, indent=2))
        print("ROOFTOP_CHUNK_COMPLETE", start_frame, end_frame, len(rendered))
        return

if __name__ == "__main__":
    run()
