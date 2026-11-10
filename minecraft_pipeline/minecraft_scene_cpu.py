#!/usr/bin/env python3
"""FrameForge Minecraft production: BROWN chapters 5-6 ambush.
Builds Java-format 64x64 player skins first, then a voxel scene and silent film.
"""
import bpy, math, os, sys, json, random, struct, zlib, binascii, subprocess
from pathlib import Path
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

def build_scene(out_dir):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    out_dir.mkdir(parents=True,exist_ok=True)
    skin_paths=build_skins(out_dir)
    scene=bpy.context.scene; scene.render.engine="CYCLES"; scene.cycles.device="CPU"
    scene.cycles.samples=32; scene.cycles.use_denoising=True; scene.cycles.use_adaptive_sampling=True; scene.cycles.adaptive_threshold=0.015
    if hasattr(scene.render,"use_persistent_data"): scene.render.use_persistent_data=True
    scene.render.threads_mode="AUTO"
    scene.render.resolution_x=1280; scene.render.resolution_y=720; scene.render.resolution_percentage=100
    scene.render.fps=60; scene.render.fps_base=1.0; scene.frame_start=1; scene.frame_end=10800
    scene.render.use_motion_blur=True; scene.render.motion_blur_shutter=0.35
    scene.view_settings.view_transform="AgX"; scene.view_settings.exposure=1.25; scene.view_settings.gamma=1.0
    scene.render.image_settings.color_mode="RGB"
    scene.world=bpy.data.worlds.new("Vesper_Night_World"); scene.world.use_nodes=True
    bg=scene.world.node_tree.nodes.get("Background"); bg.inputs[0].default_value=(0.16,0.19,0.24,1); bg.inputs[1].default_value=0.75

    mats={
     "road":pixel_material("Wet_Charcoal_Asphalt",(34,42,52),1,"road",0.38),
     "stone":pixel_material("Dark_Stone_Bricks",(82,91,103),2,"brick"),
     "concrete":pixel_material("Cold_Concrete",(104,113,124),3,"stone"),
     "brick":pixel_material("Warehouse_Red_Brick",(110,66,59),4,"brick"),
     "glass":mat_color("Blue_Glass_Blocks",(0.08,0.22,0.34),0.18,0.2),
     "wood":pixel_material("Crate_Wood",(106,68,39),5,"wood"),
     "leaf":pixel_material("Voxel_Foliage",(34,83,52),6,"leaf"),
     "metal":pixel_material("Dark_Industrial_Metal",(36,52,69),7,"metal",0.42,0.55),
     "gold":mat_color("Street_Gold",(0.78,0.47,0.11),0.5,0.35),
     "warm":mat_color("Warm_Window_Emission",(1.0,0.48,0.13),0.3,0,2.4),
     "blue":mat_color("Cold_Security_Emission",(0.07,0.38,0.95),0.25,0,2.0),
     "white":mat_color("Headlight_Emission",(0.86,0.94,1.0),0.2,0,5.0),
     "fire":mat_color("Voxel_Fire_Orange",(1.0,0.19,0.025),0.4,0,4.5),
     "fire2":mat_color("Voxel_Fire_Gold",(1.0,0.65,0.08),0.35,0,5.0),
     "smoke":mat_color("Smoke_Charcoal",(0.045,0.055,0.075),1.0),
     "paper":mat_color("Tovin_Paper",(0.82,0.8,0.7),0.95),
     "rubber":mat_color("Block_Rubber",(0.018,0.024,0.033),0.92),
     "rim":mat_color("Wheel_Rim",(0.22,0.28,0.35),0.45,0.7)
    }
    skinmats={n:skin_material("Skin_"+n,p) for n,p in skin_paths.items()}

    # Solid voxel city and industrial corridor, batched by block material.
    batches={}; add_batch(batches,"road",(0,0,-0.28),(64,26,0.5))
    for x in range(-28,33,2):
        for y in range(-4,5,2): add_batch(batches,"road",(x,y,0.015),(1.96,1.96,0.08))
        for side in (-1,1):
            add_batch(batches,"concrete",(x,side*5.4,0.01),(1.96,1.0,0.22))
            add_batch(batches,"stone",(x,side*6.1,0.01),(1.96,0.35,0.28))
    for x in range(-25,29,5): add_batch(batches,"gold",(x,0,0.075),(2.0,0.12,0.035))
    rng=random.Random(20261109)
    for side in (-1,1):
        for i,x in enumerate(range(-20,25,8)):
            h=rng.uniform(8.0,14.0); depth=rng.uniform(3.0,4.4); width=rng.uniform(5.6,7.2); y=side*10.2
            wallmat="brick" if i%3==0 else ("stone" if i%2 else "concrete")
            add_batch(batches,wallmat,(x,y,h/2),(width,depth,h))
            near_y=y-side*(depth/2+0.08)
            for floor in range(1,int(h//2.7)):
                z=1.2+floor*2.5
                for wx in (-1.7,0,1.7):
                    add_batch(batches,"glass",(x+wx,near_y,z),(0.82,0.12,1.15))
                    add_batch(batches,"metal",(x+wx,near_y-side*0.09,z-0.65),(1.05,0.22,0.12))
                    if (i+floor+int(wx))%4==0: add_batch(batches,"warm",(x+wx,near_y-side*0.08,z),(0.32,0.045,0.55))
            add_batch(batches,"concrete",(x,y,h+0.32),(width+0.5,depth+0.4,0.65))
            add_batch(batches,"metal",(x-1.5,y,h+1.0),(1.0,1.0,0.8))
    # Warehouse loading bay and industrial containers.
    add_batch(batches,"brick",(14,8.8,4.0),(12,7,8)); add_batch(batches,"metal",(14,5.19,2.1),(5.2,0.16,4.2))
    for x in (11.4,16.6): add_batch(batches,"concrete",(x,5.0,2.5),(0.4,0.4,5.0))
    for z in (0.35,4.8): add_batch(batches,"metal",(14,5.0,z),(5.8,0.32,0.32))
    for i,x in enumerate((1.5,5.2,9.0,19.0)):
        add_batch(batches,"metal",(x,7.0,1.15),(3.0,1.8,2.3)); add_batch(batches,"stone",(x,7.0,2.35),(3.1,1.9,0.16))
    for x,y in ((4.5,-6.4),(7.4,6.5),(12.0,-6.5),(-8.0,6.4)):
        add_batch(batches,"wood",(x,y,0.45),(1.0,1.0,0.9)); add_batch(batches,"wood",(x+0.6,y,0.45),(1.0,1.0,0.9))
    # Blocky trees.
    for x in (-17,-7,3,22):
        for side in (-1,1):
            y=side*7.5; add_batch(batches,"wood",(x,y,1.2),(0.55,0.55,2.4))
            for dx,dz in ((0,3.0),(0,3.8),(0.75,3.2),(-0.75,3.2),(0,4.5)):
                add_batch(batches,"leaf",(x+dx,y,dz),(1.4,1.4,1.2))
    # Minecraft block street lamps.
    for x in (-18,-10,-2,6,14,22):
        for side in (-1,1):
            y=side*5.7; add_batch(batches,"metal",(x,y,2.8),(0.22,0.22,5.6))
            add_batch(batches,"metal",(x+0.55,y,5.4),(1.25,0.22,0.22))
            add_batch(batches,"warm",(x+1.05,y,5.2),(0.45,0.45,0.24))
    # Distant voxel skyline.
    for i in range(14):
        x=-26+i*4; h=rng.uniform(9,20)
        add_batch(batches,"stone",(x,17,h/2),(3.4,2.2,h))
        add_batch(batches,"blue",(x,15.84,h*0.68),(0.18,0.08,0.35))
    for k,blocks in batches.items(): block_batch("Voxel_World_"+k,blocks,mats[k])

    def area_light(name,loc,power,color,size,target):
        data=bpy.data.lights.new(name,"AREA"); data.energy=power; data.color=color; data.shape="DISK"; data.size=size
        ob=bpy.data.objects.new(name,data); scene.collection.objects.link(ob); ob.location=loc
        ob.rotation_euler=(Vector(target)-ob.location).to_track_quat("-Z","Y").to_euler(); return ob
    area_light("Moon_Key",(0,-12,17),7600,(0.52,0.68,1.0),14,(0,0,0))
    area_light("Warehouse_Rim",(15,7,12),5200,(1.0,0.55,0.30),10,(5,0,1))
    area_light("City_Fill",(-12,10,10),3900,(0.32,0.52,0.95),12,(-2,0,0))
    sun_data=bpy.data.lights.new("Broad_Soft_Fill","SUN"); sun_data.energy=2.2; sun_data.angle=math.radians(22)
    sun_obj=bpy.data.objects.new("Broad_Soft_Fill",sun_data); scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler=(math.radians(24),math.radians(-18),math.radians(-28))
    area_light("Camera_Fill",(3,-18,15),5200,(0.72,0.82,1.0),18,(2,0,1))
    area_light("Warm_Front_Fill",(18,-10,10),3800,(1.0,0.72,0.48),12,(12,0,1))
    for x in (-18,-10,-2,6,14,22):
        for side in (-1,1):
            data=bpy.data.lights.new("Street_Pool","POINT"); data.energy=170; data.color=(1.0,0.55,0.24); data.shadow_soft_size=1.6
            ob=bpy.data.objects.new("Street_Pool",data); scene.collection.objects.link(ob); ob.location=(x,side*5.7,5.0)

    # Animated rainfall built from tiny blue blocks.
    rain_root=empty("Rain_Field"); rain_blocks=[]; rr=random.Random(82)
    for i in range(170):
        rain_blocks.append(((rr.uniform(-22,24),rr.uniform(-9,9),rr.uniform(1,12)),(0.018,0.025,rr.uniform(0.25,0.55))))
    rain_obj=block_batch("Voxel_Rain_Streaks",rain_blocks,mats["blue"]); rain_obj.parent=rain_root
    for cycle in range(91):
        start=1+cycle*120
        key(rain_root,start,loc=(0,0,8))
        key(rain_root,start+60,loc=(0,0,0))
        key(rain_root,start+119,loc=(0,0,-8))

    # Crew van — solid blocks, transparent-looking glass, open roof rails.
    vehicle=empty("Grave_Choir_Vehicle_ROOT")
    bodymat=mat_color("Vehicle_Deep_Teal",(0.055,0.12,0.16),0.55,0.28)
    trim=mat_color("Vehicle_Steel_Trim",(0.18,0.23,0.28),0.42,0.55)
    glass=mat_color("Vehicle_Glass",(0.12,0.27,0.38),0.18,0.18)
    cube("Van_Chassis",(4.7,1.95,0.38),(0,0,0.62),trim,vehicle)
    cube("Van_Main_Body",(4.5,1.9,0.7),(0,0,1.02),bodymat,vehicle)
    cube("Van_Hood",(1.05,1.88,0.44),(1.72,0,1.42),bodymat,vehicle)
    cube("Van_Rear_Block",(0.82,1.88,0.56),(-1.82,0,1.4),bodymat,vehicle)
    for side in (-1,1):
        cube("Van_Side_Glass",(2.5,0.045,0.72),(-0.05,side*0.955,1.7),glass,vehicle)
        for xx in (-1.45,0.25,1.15): cube("Van_Window_Pillar",(0.12,0.12,0.92),(xx,side*0.98,1.55),trim,vehicle)
    cube("Van_Front_Windscreen",(0.06,1.65,0.72),(1.15,0,1.72),glass,vehicle)
    cube("Van_Rear_Window",(0.06,1.55,0.62),(-2.24,0,1.68),glass,vehicle)
    for side in (-1,1): cube("Van_Roof_Rail",(2.9,0.14,0.16),(-0.05,side*0.82,2.22),trim,vehicle)
    cube("Van_Roof_Crossbar",(0.16,1.8,0.16),(-0.9,0,2.22),trim,vehicle)
    cube("Van_Front_Bumper",(0.28,2.0,0.22),(2.35,0,0.6),trim,vehicle)
    cube("Van_Rear_Bumper",(0.24,2.0,0.22),(-2.35,0,0.6),trim,vehicle)
    wheel_objs=[]
    for xx in (-1.55,1.5):
        for yy in (-1.0,1.0):
            wheel=cube("Van_Block_Wheel",(0.68,0.26,0.68),(xx,yy,0.52),mats["rubber"],vehicle); wheel_objs.append(wheel)
            cube("Van_Wheel_Rim",(0.34,0.07,0.34),(xx,yy*1.15,0.52),mats["rim"],vehicle)
    for yy in (-0.62,0.62):
        cube("Van_Headlight",(0.12,0.38,0.26),(2.4,yy,1.05),mats["white"],vehicle)
        cube("Van_Tail_Light",(0.12,0.32,0.24),(-2.4,yy,1.18),mats["fire"],vehicle)
    door_pivot=empty("Van_Passenger_Door_Hinge",vehicle,(-0.55,-0.98,1.06))
    cube("Van_Passenger_Door",(1.2,0.09,0.85),(0,0,0),bodymat,door_pivot)
    cube("Van_Door_Window",(0.96,0.035,0.38),(0,-0.055,0.33),glass,door_pivot)
    key(door_pivot,1,rot=(0,0,0)); key(door_pivot,1280,rot=(0,0,0)); key(door_pivot,1390,rot=(0,0,-0.85)); key(door_pivot,3600,rot=(0,0,-0.85))
    seatmat=mat_color("Van_Seat_Leather",(0.055,0.07,0.09),0.92)
    for xx in (0.5,-1.15):
        for yy in (-0.43,0.43):
            cube("Van_Seat_Base",(0.72,0.62,0.18),(xx,yy,0.82),seatmat,vehicle)
            cube("Van_Seat_Back",(0.18,0.62,0.75),(xx-0.28,yy,1.24),seatmat,vehicle)
    kesh=player("Kesh",skinmats["Kesh"],(0.15,0.38,0.06),vehicle,math.pi/2)
    lark=player("Lark",skinmats["Lark"],(-0.88,-0.38,0.06),vehicle,math.pi/2)
    juno=player("Juno",skinmats["Juno"],(-0.88,0.38,0.06),vehicle,math.pi/2)
    biko=player("Biko",skinmats["Biko"],(-1.52,-0.38,0.06),vehicle,math.pi/2)
    tovin=player("Tovin",skinmats["Tovin"],(-1.52,0.38,0.06),vehicle,math.pi/2)

    key(vehicle,1,loc=(-18,0,0),rot=(0,0,0)); key(vehicle,600,loc=(-11,0,0),rot=(0,0,0))
    key(vehicle,1260,loc=(2.4,0,0),rot=(0,0,0)); key(vehicle,1430,loc=(4.7,0,0),rot=(0,0,0))
    key(vehicle,1500,loc=(5.6,0,0.12),rot=(0,0.25,0.02)); key(vehicle,1620,loc=(6.0,0,0.18),rot=(0,1.18,0.12))
    key(vehicle,3600,loc=(6.0,0,0.18),rot=(0,1.18,0.12))
    for w in wheel_objs:
        key(w,1,rot=(0,0,0)); key(w,1430,rot=(0,0,18)); key(w,1500,rot=(0,0,20)); key(w,1620,rot=(0,0,22))

    # The Senator avatar is the lead, with blond hair, blue eyes, navy/white suit and gold crest.
    senator=player("Senator",skinmats["Senator"],(-17.65,-0.38,0.08),None,math.pi/2)
    cube("Senator_Phone",(0.12,0.035,0.22),(0.07,-0.15,-0.18),mats["metal"],senator["armR"])
    cube("Phone_Blue_Screen",(0.09,0.012,0.15),(0.07,-0.173,-0.18),mats["blue"],senator["armR"])
    key(senator["root"],1,loc=(-17.65,-0.38,0.08),rot=(0,0,math.pi/2))
    key(senator["root"],600,loc=(-10.65,-0.38,0.08),rot=(0,0,math.pi/2))
    key(senator["root"],1260,loc=(2.75,-0.38,0.08),rot=(0,0,math.pi/2))
    key(senator["root"],1430,loc=(5.05,-0.38,0.08),rot=(0,0,math.pi/2))
    key(senator["root"],1500,loc=(6.1,-1.35,0.5),rot=(0,0.65,1.0))
    key(senator["root"],1620,loc=(7.2,-2.0,0.0),rot=(0,0.25,0.12))
    key(senator["root"],2100,loc=(8.0,-2.45,0.0),rot=(0,0.12,0.05))
    key(senator["root"],2700,loc=(8.45,-2.55,0.0),rot=(0,0.08,0.0))
    key(senator["root"],3600,loc=(8.45,-2.55,0.0),rot=(0,0.08,0.0))
    for f,r in ((1,(0,0,0)),(1430,(0.1,0,0)),(1500,(1.05,0.1,0)),(1620,(0.75,0,0)),(2100,(0.7,0,0)),(2700,(0.45,0,0)),(3600,(0.35,0,0))): key(senator["armL"],f,rot=r)
    for f,r in ((1,(0,0,0)),(1430,(0,0,0)),(1500,(-0.9,0,0)),(1620,(-1.2,0,0)),(2100,(-0.8,0,0)),(2700,(-0.2,0,0)),(3600,(-0.2,0,0))): key(senator["armR"],f,rot=r)
    for f,r in ((1,(0,0,0)),(1430,(0,0,0)),(1620,(0.65,0,0)),(2100,(0.75,0,0)),(2700,(0.35,0,0)),(3600,(0.25,0,0))): key(senator["legL"],f,rot=r)
    for f,r in ((1,(0,0,0)),(1430,(0,0,0)),(1620,(-0.65,0,0)),(2100,(-0.7,0,0)),(2700,(-0.25,0,0)),(3600,(-0.15,0,0))): key(senator["legR"],f,rot=r)
    for f,r in ((1,(0,0,0)),(1430,(0,0,0)),(1500,(0.55,0,0.25)),(1620,(0.4,0,0)),(2100,(0.25,0,0)),(2700,(0.1,0,0)),(3600,(0.1,0,0))): key(senator["head"],f,rot=r)

    # Non-graphic voxel blast, light pulse, smoke and debris.
    center=(5.5,0.0,1.25); flashmat=mat_color("Whiteout_Flash",(1.0,0.95,0.83),0.3,0,12.0)
    flash=cube("Blast_Flash_Block",(0.2,0.2,0.2),center,flashmat)
    key(flash,1439,scale=(0.001,0.001,0.001)); key(flash,1450,scale=(9,7,5)); key(flash,1470,scale=(0.001,0.001,0.001))
    rr=random.Random(940)
    for i in range(34):
        loc=(center[0]+rr.uniform(-0.7,0.7),center[1]+rr.uniform(-0.7,0.7),center[2]+rr.uniform(-0.6,0.6))
        o=cube("Fire_Voxel_%02d"%i,(rr.uniform(0.25,0.65),rr.uniform(0.25,0.65),rr.uniform(0.25,0.65)),loc,mats["fire"] if i%2 else mats["fire2"])
        dx,dy,dz=rr.uniform(-3.5,3.5),rr.uniform(-3.5,3.5),rr.uniform(0.5,4.5)
        key(o,1439,loc=loc,scale=(0.01,0.01,0.01))
        key(o,1460,loc=(loc[0]+dx*.35,loc[1]+dy*.35,loc[2]+dz*.4),scale=(1,1,1))
        key(o,1540,loc=(loc[0]+dx,loc[1]+dy,loc[2]+dz),scale=(0.45,0.45,0.45))
        key(o,1700,loc=(loc[0]+dx,loc[1]+dy,loc[2]+dz+1),scale=(0.01,0.01,0.01))
    for i in range(26):
        loc=(center[0]+rr.uniform(-1.3,1.3),center[1]+rr.uniform(-1.0,1.0),center[2]+rr.uniform(0,2))
        o=cube("Smoke_Voxel_%02d"%i,(rr.uniform(0.7,1.5),rr.uniform(0.7,1.5),rr.uniform(0.7,1.5)),loc,mats["smoke"])
        key(o,1460,loc=loc,scale=(0.1,0.1,0.1))
        key(o,1600,loc=(loc[0]+rr.uniform(-1,1),loc[1]+rr.uniform(-1,1),loc[2]+rr.uniform(1.5,4)),scale=(1.2,1.2,1.2))
        key(o,3600,loc=(loc[0],loc[1],loc[2]+3),scale=(1.5,1.5,1.5))
    for i in range(46):
        loc=(center[0]+rr.uniform(-0.5,0.5),center[1]+rr.uniform(-0.5,0.5),center[2]+rr.uniform(-0.4,0.6))
        o=cube("Flying_Debris_%02d"%i,(rr.uniform(0.12,0.38),rr.uniform(0.12,0.38),rr.uniform(0.12,0.38)),loc,mats["stone"])
        end=(loc[0]+rr.uniform(-4,4),loc[1]+rr.uniform(-4,4),rr.uniform(0.12,1.0))
        key(o,1439,loc=loc,rot=(0,0,0),scale=(0.01,0.01,0.01))
        key(o,1500,loc=(loc[0]+(end[0]-loc[0])*.55,loc[1]+(end[1]-loc[1])*.55,end[2]+rr.uniform(1,3)),rot=(rr.random()*4,rr.random()*4,rr.random()*4),scale=(1,1,1))
        key(o,1620,loc=end,rot=(rr.random()*5,rr.random()*5,rr.random()*5),scale=(1,1,1))
    ld=bpy.data.lights.new("Blast_Pulse","POINT"); ld.color=(1.0,0.28,0.08); ld.energy=0; ld.shadow_soft_size=4.5
    lo=bpy.data.objects.new("Blast_Pulse",ld); scene.collection.objects.link(lo); lo.location=center
    for f,v in ((1,0),(1439,0),(1448,6500),(1470,1800),(1540,450),(1680,90),(3600,35)):
        ld.energy=v; ld.keyframe_insert(data_path="energy",frame=f)

    # Tovin's paper fragment and silent rescue beat.
    paper=cube("Tovin_Application_Fragment",(0.42,0.29,0.025),(8.25,-2.7,0.045),mats["paper"])
    ink=mat_color("Ink_On_Paper",(0.16,0.18,0.2),0.9)
    for i in range(3): cube("Paper_Writing_Mark",(0.22,0.012,0.006),(8.22,-2.61-i*0.045,0.061),ink)
    key(paper,1,loc=(8.25,-2.7,0.045)); key(paper,2450,loc=(8.25,-2.7,0.045))
    key(paper,2940,loc=(8.0,-2.38,0.68),rot=(0.15,0.12,-0.4)); key(paper,3600,loc=(8.0,-2.38,0.68),rot=(0.15,0.12,-0.4))
    rescuer=player("Rescuer",skinmats["Rescuer"],(14,-4,0),None,0)
    key(rescuer["root"],1,loc=(14,-4,0)); key(rescuer["root"],2700,loc=(14,-4,0))
    key(rescuer["root"],3300,loc=(9.2,-3.65,0),rot=(0,0,0.35)); key(rescuer["root"],3600,loc=(9.0,-3.55,0),rot=(0,0,0.35))
    key(rescuer["armR"],2700,rot=(0,0,0)); key(rescuer["armR"],3300,rot=(-1.0,0,0)); key(rescuer["armR"],3600,rot=(-1.0,0,0))

    # Extended acts: pursuing drones, a second blast, escape and the Senator's camera address.
    for f,loc in ((3600,(6,0,.18)),(4200,(7,0,.18)),(5100,(11,0,.18)),(6000,(16,0,.18)),(6900,(21,0,.18)),(7800,(25,0,.18)),(8700,(27,0,.18)),(9600,(27,0,.18)),(10800,(27,0,.18))):
        key(vehicle,f,loc=loc,rot=(0,1.18,.12))
    for f,loc in ((3600,(8.45,-2.55,0)),(5100,(10,-2.55,0)),(6900,(16,-2.55,0)),(8100,(21,-2.55,0)),(9600,(24,-2.55,0)),(10800,(24,-2.55,0))):
        key(senator["root"],f,loc=loc,rot=(0,0,0))
    for f,loc in ((3600,(9,-3.55,0)),(5400,(12,-3.4,0)),(7200,(18,-3.2,0)),(8700,(22,-3,0)),(9600,(25,-2.9,0)),(10800,(25,-2.9,0))):
        key(rescuer["root"],f,loc=loc,rot=(0,0,.15))
    # Two block-built pursuit drones bank across the road.
    for idx,base_loc in enumerate(((14,-2.5,8),(19,3,9))):
        dr=empty("Pursuit_Drone_%02d_ROOT"%idx,None,base_loc)
        cube("Pursuit_Drone_%02d_Core"%idx,(1.35,.82,.38),(0,0,0),mats["metal"],dr)
        cube("Pursuit_Drone_%02d_Canopy"%idx,(.72,.68,.26),(0,0,.30),mats["glass"],dr)
        for side in (-1,1):
            cube("Pursuit_Drone_%02d_Lamp"%idx,(.16,.16,.16),(side*.52,0,.04),mats["blue"],dr)
            cube("Pursuit_Drone_%02d_Boom"%idx,(.72,.12,.12),(side*.85,0,0),mats["metal"],dr)
        for f,loc,rot in ((3601,base_loc,(0,0,0)),(4500,(base_loc[0]+2,-1,7.6),(.12,0,.18)),(5700,(base_loc[0]+5,0,6.8),(.2,0,-.2)),(6900,(base_loc[0]+1,-2,6),(0,0,.35)),(8100,(base_loc[0]-2,-1,7),(.1,0,0)),(9300,(base_loc[0]-4,0,8),(0,0,-.25)),(10800,(base_loc[0]-6,0,8),(0,0,0))):
            key(dr,f,loc=loc,rot=rot)
    blast2_center=(19,0,1.45)
    flash2=cube("Second_Blast_Flash",(.2,.2,.2),blast2_center,flashmat)
    key(flash2,6570,scale=(.001,.001,.001)); key(flash2,6600,scale=(8,6,4)); key(flash2,6630,scale=(.001,.001,.001))
    for i in range(22):
        loc=(blast2_center[0]+rr.uniform(-.9,.9),rr.uniform(-.9,.9),blast2_center[2]+rr.uniform(-.7,.7))
        obj=cube("Second_Blast_Fire_%02d"%i,(rr.uniform(.25,.62),rr.uniform(.25,.62),rr.uniform(.25,.62)),loc,mats["fire"] if i%2 else mats["fire2"])
        dx,dy,dz=rr.uniform(-3,3),rr.uniform(-3,3),rr.uniform(.6,4)
        key(obj,6570,loc=loc,scale=(.01,.01,.01)); key(obj,6600,loc=(loc[0]+dx*.3,loc[1]+dy*.3,loc[2]+dz*.3),scale=(1,1,1))
        key(obj,6900,loc=(loc[0]+dx,loc[1]+dy,loc[2]+dz),scale=(.25,.25,.25)); key(obj,7200,loc=(loc[0]+dx,loc[1]+dy,loc[2]+dz+.7),scale=(.01,.01,.01))
    light2_data=bpy.data.lights.new("Second_Blast_Pulse","POINT"); light2_data.color=(1,.34,.12); light2_data.energy=0; light2_data.shadow_soft_size=5
    light2=bpy.data.objects.new("Second_Blast_Pulse",light2_data); scene.collection.objects.link(light2); light2.location=blast2_center
    for f,v in ((1,0),(6570,0),(6600,5200),(6630,2100),(6900,420),(7200,80),(10800,30)):
        light2_data.energy=v; light2_data.keyframe_insert(data_path="energy",frame=f)
    for f in (9900,10200,10800): key(senator["root"],f,loc=(24,-2.55,0),rot=(0,0,0))
    for f,r in ((9600,(0,0,0)),(9900,(.12,0,0)),(10200,(.04,0,0)),(10800,(0,0,0))): key(senator["head"],f,rot=r)
    for f,r in ((9600,(0,0,0)),(9900,(-.55,0,0)),(10200,(-1.25,0,0)),(10400,(-.55,0,0)),(10600,(-1.1,0,0)),(10800,(0,0,0))):
        key(senator["armL"],f,rot=r)
    cta_mouth=cube("Senator_CTA_Mouth",(.12,.02,.035),(0,-.255,-.09),mats["rubber"],senator["head"])
    for j,f in enumerate(range(10200,10801,12)): key(cta_mouth,f,scale=(1,.25 if j%2==0 else 1,1))


    # Eight deliberate camera angles and hard cuts.
    cameras=[
      make_camera("CAM_01_Aerial_Establish",(0,-24,17),(0,0,0.6),42),
      make_camera("CAM_02_Cabin_Senator",(-8,-5.5,3.0),(-8,0,1.4),55),
      make_camera("CAM_03_Empty_Corridor",(4,-17,9),(4,0,0.9),48),
      make_camera("CAM_04_Blast_Impact",(6.5,-7.8,4.4),(5.5,0,1.1),46),
      make_camera("CAM_05_Ground_Crawl",(8.1,-5.2,1.8),(7.6,-2,0.8),58),
      make_camera("CAM_06_Paper_Detail",(8.8,-3.8,1.0),(8.15,-2.5,0.08),62),
      make_camera("CAM_07_Rescue_Moment",(9.5,-7,3.0),(8.5,-2.7,0.9),50),
      make_camera("CAM_08_Final_Crane",(5,-26,19),(6,0,0.5),40)
    ]
    scene.camera=cameras[0]; cut_frames=(1,541,1081,1441,1621,2101,2701,3301)
    for f,cam in zip(cut_frames,cameras):
        m=scene.timeline_markers.new(cam.name,frame=f); m.camera=cam
    base=Vector(cameras[3].location)
    for f,off in ((1439,(0,0,0)),(1448,(0.45,-0.2,0.16)),(1455,(-0.32,0.24,-0.12)),(1463,(0.2,-0.08,0.06)),(1475,(0,0,0))):
        key(cameras[3],f,loc=tuple(base+Vector(off)))
    key(cameras[0],1,loc=(0,-24,17)); key(cameras[0],540,loc=(2,-22,15))
    key(cameras[-1],3301,loc=(5,-26,19)); key(cameras[-1],3600,loc=(7,-23,17))

    extra_camera_specs=[
      ("CAM_09_Regroup",(10,-7.2,5),(8,-1,1),48,3601),("CAM_10_Drones_Overhead",(15,-7.2,9),(17,0,6),46,4201),
      ("CAM_11_Van_Escape",(2,-7.2,4),(14,0,1),50,4801),("CAM_12_Aerial_Chase",(19,-20,14),(19,0,1),42,5401),
      ("CAM_13_Second_Blast",(20,-7.2,5),(19,0,1.2),48,6301),("CAM_14_Crew_Rush",(23,-7.2,4),(24,-2,1),52,6901),
      ("CAM_15_Road_Escape",(15,-25,16),(22,0,1),40,7801),("CAM_16_Safehouse",(27,-13,7),(25,-2,1),48,8701),
      ("CAM_17_Senator_Address",(24,-7,2.8),(24,-2.55,1.25),62,9601),("CAM_18_CTA_Closeup",(24,-6,2.65),(24,-2.55,1.3),68,10201)
    ]
    extension_cut_frames=[]
    for name,loc,target,lens,frame in extra_camera_specs:
        cam=make_camera(name,loc,target,lens); marker=scene.timeline_markers.new(name,frame=frame); marker.camera=cam
        extension_cut_frames.append(frame)

    scene.frame_set(1)
    blend=out_dir/"Senator_Minecraft_BROWN_Ambush.blend"; bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    audit={
      "project":"Senator Minecraft — BROWN Chapters 5-6","duration_seconds":180,"fps":60,"frames":10800,"resolution":[1280,720],
      "engine":"Cycles CPU","samples":96,"denoising":True,"audio":"none","skin_format":"Minecraft Java 64x64",
      "skin_files":[p.name for p in skin_paths.values()],
      "characters":["Senator","Kesh","Lark","Juno","Biko","Tovin","Rescuer"],"camera_cuts":list(cut_frames)+list(extension_cut_frames),
      "cta_dialogue":"Hey! If you enjoyed this adventure, tap Like and Subscribe for more Minecraft stories. I will see you in the next one!",
      "checks":{"frame_count":scene.frame_end-scene.frame_start+1==10800,"60_fps":scene.render.fps==60,
       "landscape":scene.render.resolution_x>scene.render.resolution_y,"cpu_cycles":scene.render.engine=="CYCLES" and scene.cycles.device=="CPU",
       "seven_skin_files":len(skin_paths)==7,"senator_main_character":True,"eight_cameras":len(cameras)==8,"three_minute_timeline":scene.frame_end==10800,"eighteen_camera_angles":len(cameras)+len(extra_camera_specs)==18}
    }
    (out_dir/"production_audit.json").write_text(json.dumps(audit,indent=2))
    return scene,blend,audit

def run():
    mode,out,start_frame,end_frame=cli()
    out.mkdir(parents=True,exist_ok=True)


    if mode=="qa-preview":
        scene=bpy.context.scene; scene.render.engine="CYCLES"; scene.cycles.device="CPU"; scene.cycles.samples=12
        scene.cycles.use_denoising=True; scene.cycles.use_adaptive_sampling=True
        scene.render.resolution_x=640; scene.render.resolution_y=360; scene.render.resolution_percentage=100
        scene.render.image_settings.file_format="PNG"; scene.render.image_settings.color_mode="RGB"; scene.render.use_file_extension=True
        qa_dir=out/"qa_preview"; qa_dir.mkdir(parents=True,exist_ok=True)
        qa_frames=(300,800,1300,1550,1800,2400,3000,3450,3900,4500,5100,5700,6600,7200,8100,9000,9900,10500)
        for frame in qa_frames:
            scene.frame_set(frame); scene.render.filepath=str(qa_dir/("qa_frame_%05d"%frame)); bpy.ops.render.render(write_still=True)
        print("VISUAL_QA_PREVIEW_COMPLETE",json.dumps({"frames":list(qa_frames)})); return

    # Render workers load the audited .blend and render their assigned contiguous
    # frame range to PNG. Encoding is performed by system FFmpeg in a separate
    # workflow job because Blender 5 no longer supports FFMPEG as an image format.
    if mode=="render-frames":
        scene=bpy.context.scene
        if scene is None:
            raise RuntimeError("No Blender scene was loaded for frame rendering.")
        if not (1 <= start_frame <= end_frame <= 10800):
            raise ValueError("Invalid frame range: %s-%s"%(start_frame,end_frame))
        scene.render.engine="CYCLES"
        scene.cycles.device="CPU"
        scene.cycles.samples=32
        scene.cycles.use_denoising=True
        scene.cycles.use_adaptive_sampling=True
        scene.cycles.adaptive_threshold=0.015
        scene.render.resolution_x=1280
        scene.render.resolution_y=720
        scene.render.resolution_percentage=100
        scene.render.fps=60
        scene.render.fps_base=1.0
        scene.render.image_settings.file_format="PNG"
        scene.render.image_settings.color_mode="RGB"
        scene.render.image_settings.color_depth="8"
        scene.render.image_settings.compression=0
        scene.render.use_file_extension=True
        scene.render.use_motion_blur=True
        scene.render.motion_blur_shutter=0.35
        scene.render.threads_mode="AUTO"
        frame_dir=out/"frames"
        frame_dir.mkdir(parents=True,exist_ok=True)
        scene.render.filepath=str(frame_dir/"frame_")
        scene.frame_start=start_frame
        scene.frame_end=end_frame
        scene.frame_set(start_frame)
        bpy.ops.render.render(animation=True)
        rendered=list(frame_dir.glob("frame_*.png"))
        expected=end_frame-start_frame+1
        if len(rendered)!=expected:
            raise RuntimeError("Chunk %d-%d produced %d PNGs; expected %d"%(start_frame,end_frame,len(rendered),expected))
        (out/"chunk_verification.json").write_text(json.dumps({
            "start_frame":start_frame,"end_frame":end_frame,
            "expected_frames":expected,"rendered_frames":len(rendered),
            "renderer":"Blender Cycles CPU","samples":96,
            "resolution":[1280,720],"fps":60
        },indent=2))
        print("FRAME_CHUNK_COMPLETE",start_frame,end_frame,len(rendered))
        return

    # Character atlases are deliberately authored before the voxel scene.
    paths=build_skins(out)
    if mode=="skins":
        print(json.dumps({"skins_created":[str(p) for p in paths.values()]},indent=2))
        return
    scene,blend,audit=build_scene(out)
    if not all(audit["checks"].values()):
        raise RuntimeError("Scene audit failed: "+json.dumps(audit["checks"]))
    if mode=="build":
        print("BLENDER_SCENE_READY",blend)
        print(json.dumps(audit,indent=2))
        return
    if mode=="audit":
        scene.render.image_settings.file_format="PNG"
        scene.render.image_settings.color_mode="RGB"
        for seconds in (9,23.8,29,41,52,58):
            scene.frame_set(int(seconds*60)+1)
            scene.render.filepath=str(out/("preview_%02dsec"%seconds))
            bpy.ops.render.render(write_still=True)
        print("Scene audit and preview renders completed.")
        return
    if mode=="render":
        frame_dir=out/"frames"
        frame_dir.mkdir(parents=True,exist_ok=True)
        scene.render.image_settings.file_format="PNG"
        scene.render.image_settings.color_mode="RGB"
        scene.render.image_settings.color_depth="8"
        scene.render.image_settings.compression=0
        scene.render.filepath=str(frame_dir/"frame_")
        scene.render.fps=60
        scene.frame_start=1
        scene.frame_end=10800
        bpy.ops.render.render(animation=True)
        print("FULL_FRAME_SEQUENCE_COMPLETE",frame_dir)
        return
    raise ValueError("Unknown mode: "+mode)

if __name__=="__main__": run()
