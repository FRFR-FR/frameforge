#!/usr/bin/env python3
"""BROWN Book One: realistic 3D five-minute pilot, built and rendered in Blender."""
import argparse, json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector

FPS, WIDTH, HEIGHT = 24, 1280, 720
SHOT_SECONDS, SEGMENT_SECONDS = 25, 60
TOTAL_SECONDS, TOTAL_FRAMES = 300, 7200
MATS, COLS = {}, {}

def get_args():
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("build","render"),default="build")
    p.add_argument("--output-dir",default="output/brown_pilot")
    p.add_argument("--segment",type=int,default=1)
    return p.parse_args(argv)

def group(name):
    if name not in COLS:
        c=bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        COLS[name]=c
    return COLS[name]

def link(obj,name):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    group(name).objects.link(obj)
    return obj

def mat(name,color,rough=.65,metal=0,subsurface=0,noise=0,bump=.06,emission=0):
    if name in MATS: return MATS[name]
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    nodes=m.node_tree.nodes; links=m.node_tree.links; bs=nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value=(*color,1); bs.inputs["Roughness"].default_value=rough; bs.inputs["Metallic"].default_value=metal
    if "Subsurface Weight" in bs.inputs: bs.inputs["Subsurface Weight"].default_value=subsurface
    elif "Subsurface" in bs.inputs: bs.inputs["Subsurface"].default_value=subsurface
    if noise:
        tex=nodes.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value=noise; tex.inputs["Detail"].default_value=3
        b=nodes.new("ShaderNodeBump"); b.inputs["Strength"].default_value=bump; b.inputs["Distance"].default_value=.025
        links.new(tex.outputs["Fac"],b.inputs["Height"]); links.new(b.outputs["Normal"],bs.inputs["Normal"])
    if emission:
        s=bs.inputs.get("Emission Color") or bs.inputs.get("Emission")
        if s: s.default_value=(*color,1)
        if bs.inputs.get("Emission Strength"): bs.inputs["Emission Strength"].default_value=emission
    MATS[name]=m
    return m

def smooth(o):
    if o.type=="MESH":
        for p in o.data.polygons: p.use_smooth=True
    return o

def uv(name,loc,scale,material,collection="BROWN • Characters",parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale
    if material: o.data.materials.append(material)
    smooth(o); link(o,collection)
    if parent:
        o.parent=parent; o.matrix_parent_inverse=parent.matrix_world.inverted()
    return o

def box(name,loc,scale,material,bevel=.04,collection="BROWN • Set Dressing"):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object; o.name=name; o.dimensions=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if material: o.data.materials.append(material)
    if bevel:
        b=o.modifiers.new("Manufactured edge radii","BEVEL"); b.width=bevel; b.segments=3
        o.modifiers.new("Weighted corner normals","WEIGHTED_NORMAL")
    link(o,collection); return o

def cyl(name,loc,radius,depth,material,rotation=(0,0,0),collection="BROWN • Set Dressing"):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=radius,depth=depth,location=loc,rotation=rotation)
    o=bpy.context.object; o.name=name
    if material: o.data.materials.append(material)
    b=o.modifiers.new("Edge highlight","BEVEL"); b.width=min(.025,radius*.12); b.segments=3
    o.modifiers.new("Weighted normals","WEIGHTED_NORMAL"); link(o,collection); return o

def torus(name,loc,major,minor,material,rotation=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major,minor_radius=minor,major_segments=40,minor_segments=10,location=loc,rotation=rotation)
    o=bpy.context.object; o.name=name; o.data.materials.append(material); smooth(o); link(o,"BROWN • Set Dressing"); return o

def text(name,body,loc,size,material,rotation=(math.pi/2,0,0)):
    d=bpy.data.curves.new(name,"FONT"); d.body=body; d.size=size; d.align_x="CENTER"; d.align_y="CENTER"; d.extrude=.001
    o=bpy.data.objects.new(name,d); group("BROWN • Typography").objects.link(o); o.location=loc; o.rotation_euler=rotation; d.materials.append(material); return o

def floor(name,x,y,w,d,m):
    return box(name,(x,y,-.16),(w,d,.32),m,.025)

def area(name,loc,target,power,color,size):
    d=bpy.data.lights.new(name,"AREA"); d.energy=power; d.color=color; d.shape="DISK"; d.size=size
    o=bpy.data.objects.new(name,d); group("BROWN • Lighting").objects.link(o); o.location=loc
    o.rotation_euler=(Vector(target)-o.location).to_track_quat("-Z","Y").to_euler(); return o

def point(name,loc,power,color,size):
    d=bpy.data.lights.new(name,"POINT"); d.energy=power; d.color=color; d.shadow_soft_size=size
    o=bpy.data.objects.new(name,d); group("BROWN • Lighting").objects.link(o); o.location=loc; return o

def light_set(c,power=1000):
    area("Warm key "+str(c),(c-4,-7,8),(c,0,1.5),power,(1,.75,.55),5)
    area("Cool fill "+str(c),(c+5,-4,4),(c,0,1.6),power*.42,(.54,.68,1),4)
    area("Rim "+str(c),(c+1,4,6),(c,0,1.8),power*.65,(1,.84,.66),3)

def character(name,pos,skin,hair,jacket,trousers,hairstyle="short",height=1.0):
    root=bpy.data.objects.new(name+" • rig root",None); group("BROWN • Character Rigs").objects.link(root); root.location=pos
    sk=mat(name+" skin",skin,.5,0,.09,115,.09)
    hr=mat(name+" hair",hair,.72,0,0,170,.1)
    jk=mat(name+" tailoring",jacket,.74,0,0,210,.1)
    tr=mat(name+" trousers",trousers,.8,0,0,160,.08)
    shirt=mat(name+" shirt",(.52,.49,.43),.72,0,0,110,.05)
    shoe=mat(name+" shoes",(.025,.028,.03),.38,.08)
    white=mat(name+" eyes",(0.78,.73,.66),.26)
    iris=mat(name+" iris",(.11,.07,.045),.24)
    pupil=mat(name+" pupils",(.006,.006,.006),.15)
    lip=mat(name+" lips",(.17,.065,.055),.5)
    h=height
    def part(label,xyz,scale,m,segments=32):
        world=(pos[0]+xyz[0],pos[1]+xyz[1],pos[2]+xyz[2])
        return uv(name+" "+label,world,tuple(v*h for v in scale),m,parent=root)
    # Tailored torso and layered clothing.
    part("pelvis",(0,0,.94),(.30,.22,.32),tr)
    part("jacket",(0,0,1.48),(.39,.235,.53),jk)
    part("shirt inset",(0,-.21,1.49),(.17,.035,.38),shirt)
    part("collar",(0,-.24,1.88),(.15,.04,.10),shirt)
    part("lapel L",(-.12,-.245,1.76),(.07,.025,.23),jk)
    part("lapel R",(.12,-.245,1.76),(.07,.025,.23),jk)
    for z in (1.31,1.43,1.55): part("button",(0.025,-.266,z),(.017,.01,.017),shoe,20)
    # Legs, articulated-looking joints, boots and welt.
    for s in (-1,1):
        x=s*.17
        part("thigh "+str(s),(x,0,.69),(.15,.18,.38),tr)
        part("shin "+str(s),(x,-.01,.30),(.11,.13,.34),tr)
        part("boot "+str(s),(x,-.12,.075),(.145,.28,.105),shoe)
        part("boot sole "+str(s),(x,-.13,.025),(.15,.285,.035),shoe)
    part("neck",(0,0,2.02),(.105,.11,.15),sk)
    part("head",(0,-.015,2.36),(.255,.235,.34),sk)
    # Face is oriented toward -Y: ears, eyes, brows, nose and lips are separate detailed forms.
    for s in (-1,1):
        part("ear "+str(s),(s*.25,-.01,2.34),(.055,.07,.09),sk)
        part("eye socket "+str(s),(s*.105,-.22,2.40),(.076,.035,.052),sk)
        part("eye "+str(s),(s*.105,-.25,2.40),(.052,.026,.03),white)
        part("iris "+str(s),(s*.105,-.274,2.40),(.021,.011,.023),iris)
        part("pupil "+str(s),(s*.105,-.283,2.40),(.01,.008,.012),pupil)
        part("brow "+str(s),(s*.105,-.246,2.475),(.072,.022,.017),hr)
    part("nose bridge",(0,-.25,2.335),(.04,.05,.10),sk)
    part("nose tip",(0,-.29,2.295),(.05,.04,.04),sk)
    part("mouth",(0,-.24,2.205),(.068,.018,.017),lip)
    # Hair cap and individual shapes avoid the block silhouette of the previous prototype.
    part("hair cap",(0,.015,2.58),(.26,.24,.17),hr)
    if hairstyle=="curls":
        for ix in range(5):
            for iy in range(3):
                part("curl",( (ix-2)*.094, (iy-1)*.085, 2.65-abs(ix-2)*.006),(.073,.073,.073),hr,20)
    elif hairstyle=="bun":
        part("bun",(0,.16,2.68),(.13,.14,.14),hr)
        for s in (-1,1): part("braid "+str(s),(s*.19,.03,2.42),(.044,.065,.29),hr)
    elif hairstyle=="locs":
        for i in range(9): part("loc "+str(i),((i-4)*.052,.08,2.43),(.033,.052,.27),hr,20)
    else:
        part("hairline",(0,-.20,2.52),(.20,.035,.07),hr)
        for s in (-1,1): part("side hair "+str(s),(s*.22,.015,2.41),(.05,.18,.17),hr)
    # Shoulder, sleeve, forearm and hand volumes.
    for s in (-1,1):
        part("shoulder "+str(s),(s*.38,0,1.76),(.16,.18,.19),jk)
        part("upper sleeve "+str(s),(s*.46,0,1.55),(.13,.14,.27),jk)
        part("forearm "+str(s),(s*.51,-.055,1.20),(.105,.115,.22),jk)
        part("hand "+str(s),(s*.49,-.13,1.02),(.07,.06,.10),sk)
        part("pocket "+str(s),(s*.23,-.22,1.34),(.07,.018,.06),jk)
    root["character_name"]=name
    root["asset_status"]="PROCEDURAL CONCEPT MODEL — NOT AN APPROVED LIKENESS"
    return root

def animate(root,f0,f1,p0,p1):
    for f,p in ((f0,p0),(f1,p1)):
        root.location=p; root.keyframe_insert(data_path="location",frame=f)
    if root.animation_data and root.animation_data.action:
        for fc in root.animation_data.action.fcurves:
            for k in fc.keyframe_points: k.interpolation="BEZIER"

def camera(name,loc,target,lens=45):
    d=bpy.data.cameras.new(name); d.lens=lens; d.dof.use_dof=True; d.dof.aperture_fstop=4.5
    o=bpy.data.objects.new(name,d); group("BROWN • Cameras").objects.link(o); o.location=loc
    o.rotation_euler=(Vector(target)-o.location).to_track_quat("-Z","Y").to_euler(); return o

def shot_camera(scene,idx,center,loc,target,lens,travel):
    f0=idx*SHOT_SECONDS*FPS+1; f1=(idx+1)*SHOT_SECONDS*FPS
    c=camera("Pilot camera "+str(idx+1),loc,target,lens)
    c.keyframe_insert(data_path="location",frame=f0)
    c.location=(loc[0]+travel[0],loc[1]+travel[1],loc[2]+travel[2])
    c.keyframe_insert(data_path="location",frame=f1)
    mark=scene.timeline_markers.new("SHOT "+str(idx+1).zfill(2),frame=f0); mark.camera=c
    return c

def registry(center):
    floor("Civic registry floor",center,0,24,18,MATS["floor stone"])
    box("Civic registry rear wall",(center,8,5),(24,.45,10),MATS["limestone"],.14)
    box("Registry ceiling",(center,0,10),(24,18,.3),MATS["ceiling"])
    for x in (-9,-5,-1,3,7,11):
        box("Marble pier",(center+x,3,4.8),(.85,1.1,9.6),MATS["marble"],.1)
        box("Pier cap",(center+x,3,9.5),(1.3,1.5,.3),MATS["brass"],.04)
    for x in (-8,-4,0,4,8):
        box("Service counter",(center+x,-1,1.1),(3.2,1.2,1.5),MATS["walnut"],.1)
        box("Counter top",(center+x,-1,1.9),(3.35,1.28,.12),MATS["stone"],.03)
        box("Counter screen frame",(center+x,-.58,2.42),(.95,.08,.65),MATS["screen frame"],.03)
        box("Counter screen",(center+x,-.525,2.42),(.8,.015,.5),MATS["screen glow"],.01)
    for x in (-10,-6,-2,2,6,10):
        cyl("Queue post",(center+x,-5,.64),.06,1.25,MATS["brass"])
    text("Registry header","VESPER CIVIC REGISTER",(center,7.68,7.6),.54,MATS["gold"])
    text("Registry subheader","PUBLIC RECORDS  •  SERVICE ACCESS",(center,7.66,6.8),.19,MATS["sign"])
    floor("Records desk stage",center+40,0,10,8,MATS["walnut"])
    box("Clerk records desk",(center+40,0,.82),(4.8,2,.18),MATS["walnut"],.06)
    for i in range(8): box("Paper sheet "+str(i),(center+38.8+i*.2,-.25,.95+i*.009),(.92,1.22,.012),MATS["paper"],.002)
    cyl("Stamp handle",(center+41.2,-.1,1.16),.09,.45,MATS["brass"])
    cyl("Stamp base",(center+41.2,-.1,.95),.18,.08,MATS["metal"])
    box("Open register",(center+39.3,.4,.94),(1.65,1.15,.035),MATS["paper"],.006)
    for z in (.97,1.02):
        # Thin ink rules on the open register.
        box("Register ruling",(center+39.3,.4,z),(1.35,.008,.004),MATS["ink"],.001)
    character("Registry Clerk",(center-5,-2.6,0),(.46,.28,.20),(.04,.03,.025),(.16,.19,.21),(.07,.08,.09),"short",.94)

def corridor(center):
    floor("Public services corridor",center,0,25,13,MATS["corridor floor"])
    for y in (-5.4,5.4): box("Corridor wall",(center,y,2.5),(25,.35,5),MATS["plaster"],.05)
    box("Corridor ceiling",(center,0,5.1),(25,11,.25),MATS["ceiling"])
    for x in (-9,-5,-1,3,7,11):
        box("Service door",(center+x,-5.12,1.7),(1.7,.12,3.4),MATS["door"],.04)
        box("Door inset",(center+x,-5.04,1.8),(1.32,.025,2.9),MATS["door inset"],.02)
        cyl("Door handle",(center+x+.55,-4.96,1.55),.035,.08,MATS["brass"],(math.pi/2,0,0))
    for x in (-8,-1,6):
        box("Service counter",(center+x,3.9,1.2),(3.6,.9,1.2),MATS["walnut"],.06)
        box("Service window",(center+x,4.25,2.65),(2.7,.08,1.2),MATS["glass"],.02)
    text("Public service sign","PUBLIC SERVICES",(center,5.18,4),.30,MATS["gold"])
    for i in range(4):
        character("Anonymous visitor "+str(i+1),(center-7+i*3.5,.5,0),(.35+.03*i,.19,.13),(.025,.022,.02),(.13+.03*i,.18,.22),(.06,.07,.08),"short",.91)

def threshold(center):
    floor("Access corridor threshold",center,0,12,10,MATS["corridor floor"])
    box("Checkpoint wall",(center,4,2.5),(12,.35,5),MATS["plaster"],.05)
    for x in (-2.5,0,2.5):
        cyl("Turnstile column",(center+x,-.8,.8),.10,1.6,MATS["brass"])
        for a in (0,2*math.pi/3,4*math.pi/3):
            arm=box("Turnstile arm",(center+x,-.8,.9),(1.05,.07,.07),MATS["metal"],.025); arm.rotation_euler[2]=a
    box("Access reader",(center+2.6,-.8,1.15),(.3,.2,.65),MATS["screen frame"],.04)
    box("Reader display",(center+2.6,-.91,1.3),(.22,.02,.16),MATS["screen glow"],.01)
    text("Access threshold label","STATUS CHECK",(center,3.78,3.5),.34,MATS["gold"])

def car(name,x,y,scale,paint):
    box(name+" lower shell",(x,y,.72*scale),(2.2*scale,4.4*scale,.68*scale),paint,.20,"BROWN • Vehicles")
    box(name+" bonnet",(x,y-1.42*scale,1.03*scale),(2*scale,1.45*scale,.24*scale),paint,.11,"BROWN • Vehicles")
    box(name+" roof",(x,y+.1*scale,1.56*scale),(1.75*scale,1.95*scale,.56*scale),MATS["car frame"],.18,"BROWN • Vehicles")
    box(name+" windscreen",(x,y-.91*scale,1.50*scale),(1.58*scale,.06*scale,.5*scale),MATS["car glass"],.04,"BROWN • Vehicles")
    box(name+" rear glass",(x,y+1.08*scale,1.50*scale),(1.58*scale,.06*scale,.48*scale),MATS["car glass"],.04,"BROWN • Vehicles")
    for s in (-1,1):
        box(name+" side glass",(x+s*.89*scale,y+.12*scale,1.54*scale),(.06*scale,1.7*scale,.42*scale),MATS["car glass"],.03,"BROWN • Vehicles")
        for wy in (-1.38,1.36):
            cyl(name+" tyre",(x+s*1.08*scale,y+wy*scale,.48*scale),.42*scale,.22*scale,MATS["rubber"],(math.pi/2,0,0),"BROWN • Vehicles")
            cyl(name+" wheel hub",(x+s*1.205*scale,y+wy*scale,.48*scale),.22*scale,.03*scale,MATS["alloy"],(math.pi/2,0,0),"BROWN • Vehicles")
        box(name+" headlamp",(x+s*.72*scale,y-2.22*scale,.84*scale),(.32*scale,.05*scale,.20*scale),MATS["headlamp"],.025,"BROWN • Vehicles")
        box(name+" tail lamp",(x+s*.72*scale,y+2.22*scale,.84*scale),(.32*scale,.05*scale,.20*scale),MATS["tail lamp"],.025,"BROWN • Vehicles")
    box(name+" grille",(x,y-2.24*scale,.60*scale),(.85*scale,.035*scale,.22*scale),MATS["metal"],.02,"BROWN • Vehicles")

def city(center):
    floor("Vesper asphalt",center,0,38,22,MATS["asphalt"])
    box("Distant skyline",(center,11,9),(38,.8,18),MATS["building dark"],.06)
    for i in range(8):
        x=center-16+i*4.5; h=8+(i%3)*3
        box("Apartment tower "+str(i),(x,8,h/2),(3.8,3,h),MATS["building "+str(i%3)],.06)
        for z in range(2,int(h)-1,2):
            for dx in (-1.1,0,1.1):
                box("Tower window",(x+dx,6.47,z),(.62,.035,.88),MATS["window glow" if (i+z)%3 else "window dark"],.01)
    for i in range(11): box("Road marking",(center-17+i*3.4,0,.012),(1.7,.11,.025),MATS["road paint"],.01)
    for s in (-1,1):
        box("City pavement",(center,s*7,.06),(38,3,.18),MATS["sidewalk"],.04)
        for i in range(6):
            x=center-15+i*6
            cyl("Street lamp",(x,s*6.1,3),.055,6,MATS["metal"])
            box("Street lamp head",(x,s*6.1,6),(.55,.22,.12),MATS["lamp"],.03)
    car("Vesper taxi",center-7,2,.94,MATS["taxi"])
    car("Passing sedan",center+8,-3,.88,MATS["car paint"])
    box("City transit bus",(center+1,9,1.75),(3.3,8.4,3.1),MATS["bus"],.3,"BROWN • Vehicles")
    box("Bus windscreen",(center+1,4.77,2.1),(3.08,.035,1.2),MATS["car glass"],.05,"BROWN • Vehicles")
    for x in (center-.2,center+1,center+2.2):
        box("Bus side windows",(x,8.5,2.12),(.035,5.5,1.12),MATS["car glass"],.025,"BROWN • Vehicles")
        cyl("Bus tyre",(x,6,.62),.5,.25,MATS["rubber"],(math.pi/2,0,0),"BROWN • Vehicles")
    box("Public information display",(center-10,-6,3.2),(3.2,.22,2.2),MATS["screen frame"],.08)
    box("Display glass",(center-10,-6.14,3.2),(2.92,.035,1.92),MATS["screen glow"],.015)
    text("Public display text","VESPER  /  CITY SERVICES",(center-10,-6.18,3.35),.18,MATS["sign"])
    return character("Kaylen Atlee — street",(center-1,-1.6,0),(.37,.20,.15),(.022,.018,.016),(.09,.14,.19),(.075,.085,.10),"short",.99)

def interior(center):
    floor("Unspecified Vesper interior floor",center,0,14,12,MATS["wood"])
    box("Interior rear wall",(center,5,2.8),(14,.32,5.6),MATS["plaster"],.05)
    box("Interior side wall",(center-7,0,2.8),(.32,10,5.6),MATS["plaster"],.05)
    box("Window frame",(center+3.2,4.78,3.1),(3.8,.12,2.9),MATS["door frame"],.05)
    box("Window glass",(center+3.2,4.69,3.1),(3.48,.025,2.58),MATS["glass"],.01)
    for x in (center+1.3,center+5.1): box("Curtain",(x,4.54,3.05),(.42,.08,3.15),MATS["curtain"],.04)
    box("Interior table",(center,-.3,.82),(3.2,1.45,.16),MATS["walnut"],.06)
    for x in (center-1.35,center+1.35):
        for y in (-.8,.2): cyl("Table leg",(x,y,.38),.055,.82,MATS["metal"])
    cyl("Coffee mug",(center-.85,-.3,1.02),.15,.29,MATS["ceramic"])
    torus("Mug handle",(center-1.02,-.3,1.02),.10,.025,MATS["ceramic"],(math.pi/2,0,0))
    box("TV cabinet",(center-4,3.4,1.1),(2,.48,1.6),MATS["walnut"],.08)
    box("Television",(center-4,3.12,2.18),(1.9,.06,1.12),MATS["screen frame"],.05)
    box("TV image",(center-4,3.075,2.18),(1.74,.015,.96),MATS["screen glow"],.01)
    text("Broadcast lower third","COMMUNITY  /  RESILIENCE",(center-4,3.05,2.2),.10,MATS["sign"])
    return character("Kaylen Atlee — morning",(center-.45,-1.7,0),(.37,.20,.15),(.022,.018,.016),(.09,.14,.19),(.075,.085,.10),"short",.99)

def memory_street(center):
    floor("Memory pavement",center,0,16,12,MATS["asphalt"])
    box("Alley wall",(center,4,2.4),(16,.3,4.8),MATS["brick"],.06)
    for x in range(-7,8,2): box("Brick mortar course",(center+x,3.82,1.6),(1.7,.04,.08),MATS["mortar"],.01)
    cyl("Broken bottle body",(center-.6,-.8,.16),.10,.44,MATS["green glass"],(math.pi/2,0,0))
    cyl("Bottle neck",(center-.6,-1.05,.16),.045,.20,MATS["green glass"],(math.pi/2,0,0))
    for i in range(5):
        f=box("Glass shard "+str(i),(center-1+i*.22,-.85+(i%2)*.3,.04),(.12,.22,.018),MATS["glass shard"],.008)
        f.rotation_euler[2]=(i-2)*.31
    return character("Kaylen Atlee — memory",(center+1.2,-2.4,0),(.37,.20,.15),(.022,.018,.016),(.09,.14,.19),(.075,.085,.10),"short",.99)

def printshop(center):
    floor("Print shop floor",center,0,18,13,MATS["concrete"])
    box("Print shop rear wall",(center,5.9,2.7),(18,.35,5.4),MATS["aged plaster"],.06)
    box("Print shop left wall",(center-8.8,0,2.7),(.35,12,5.4),MATS["aged plaster"],.06)
    box("Print shop right wall",(center+8.8,0,2.7),(.35,12,5.4),MATS["aged plaster"],.06)
    for x in (-5.5,5.5): box("Black painted window",(center+x,5.68,3.25),(4.2,.05,2.2),MATS["black glass"],.02)
    text("Grave Choir wall marking","GRAVE CHOIR  ♪",(center,5.65,4.2),.58,MATS["chalk"])
    box("Old printing press",(center-6.2,2.2,.85),(2.1,1.8,1.6),MATS["press"],.1)
    cyl("Printing press roller",(center-6.2,1.1,1.05),.28,1.6,MATS["metal"],(math.pi/2,0,0))
    for i in range(4): box("Paper ream",(center-5.8+i*.24,1.1,.25),(.72,.9,.15),MATS["paper"],.01)
    box("Crew meeting table",(center,.8,.78),(6.6,2.1,.14),MATS["walnut"],.06)
    for x in (center-2.9,center+2.9):
        for y in (0,1.5): cyl("Meeting table leg",(x,y,.38),.055,.77,MATS["metal"])
    for x in (center+3.6,center+4.8):
        box("Computer monitor",(x,3.55,1.85),(1.1,.15,.9),MATS["screen frame"],.03)
        box("Monitor display",(x,3.455,1.85),(.97,.025,.75),MATS["screen glow"],.01)
        box("Monitor stand",(x,3.58,1.29),(.15,.16,.28),MATS["metal"],.02)
    for x in (center-1.8,center-1.1):
        cyl("Instant noodle cup",(x,.1,.96),.16,.28,MATS["paper"])
        torus("Noodle cup rim",(x,.1,1.10),.15,.012,MATS["brass"])
    cyl("Kettle body",(center+2.2,.1,1.12),.23,.47,MATS["kettle"])
    torus("Kettle handle",(center+2.2,.1,1.42),.18,.035,MATS["metal"],(math.pi/2,0,0))
    cyl("Kettle lid",(center+2.2,.1,1.38),.13,.055,MATS["brass"])
    box("School application",(center-.55,-.02,.97),(.72,.96,.018),MATS["paper"],.004)
    for i in range(6): box("Application line",(center-.55,-.35+i*.12,.984),(.48-(i%2)*.1,.008,.006),MATS["ink"],.001)
    cyl("Pen",(center-.05,-.05,1.04),.018,.66,MATS["pen"],(math.pi/2,0,0))
    box("Medical pouch",(center+.8,-.1,1.02),(.46,.28,.22),MATS["pouch"],.04)
    box("Pouch cross vertical",(center+.8,-.252,1.02),(.08,.018,.15),MATS["sign"],.005)
    box("Pouch cross horizontal",(center+.8,-.255,1.02),(.18,.018,.06),MATS["sign"],.005)
    for x in (-4.2,-2,2,4.2):
        box("Chair seat",(center+x,-1.1,.55),(.8,.75,.12),MATS["chair"],.05)
        box("Chair back",(center+x,-1.43,1),(.8,.12,.85),MATS["chair"],.05)
    for x in (center-5,center,center+5):
        cyl("Pendant cord",(x,0,4.45),.014,1.2,MATS["metal"])
        uv("Pendant shade",(x,0,3.8),(.35,.35,.16),MATS["brass"],"BROWN • Lighting")
        point("Warm pendant",(x,0,3.75),110,(1,.66,.36),.55)

def materials():
    mat("limestone",(.46,.43,.36),.84,noise=85)
    mat("marble",(.59,.57,.50),.34,noise=120,bump=.04)
    mat("brass",(.42,.27,.10),.28,.78)
    mat("metal",(.035,.045,.052),.33,.75,noise=115)
    mat("floor stone",(.12,.14,.16),.31,.12,noise=130)
    mat("ceiling",(.17,.18,.19),.82)
    mat("walnut",(.16,.085,.045),.38,noise=75,bump=.1)
    mat("stone",(.32,.33,.31),.28,.08)
    mat("screen frame",(.012,.018,.023),.25,.48)
    mat("screen glow",(.035,.19,.24),.22,.1,emission=1.3)
    mat("paper",(.76,.72,.61),.89,noise=175,bump=.03)
    mat("ink",(.025,.03,.04),.6)
    mat("gold",(.68,.49,.22),.32,.4)
    mat("sign",(.78,.76,.69),.35)
    mat("corridor floor",(.24,.24,.22),.55,noise=95)
    mat("plaster",(.52,.49,.42),.82,noise=90)
    mat("door",(.10,.14,.16),.45,.12)
    mat("door inset",(.16,.19,.20),.52,.08)
    mat("glass",(.045,.11,.14),.13,.28)
    mat("door frame",(.08,.09,.095),.4,.65)
    mat("asphalt",(.045,.052,.058),.94,noise=150,bump=.12)
    mat("building dark",(.04,.06,.08),.65,.22)
    for i,c in enumerate(((.12,.14,.16),(.19,.16,.14),(.12,.15,.17))): mat("building "+str(i),c,.72,.15)
    mat("window glow",(.48,.36,.18),.3,emission=1.4)
    mat("window dark",(.012,.024,.035),.24,.2)
    mat("road paint",(.72,.62,.42),.72)
    mat("sidewalk",(.22,.23,.22),.82,noise=110)
    mat("lamp",(.75,.47,.22),.25,.1,emission=2)
    mat("car paint",(.11,.17,.22),.24,.48,noise=90)
    mat("taxi",(.63,.44,.12),.28,.33,noise=85)
    mat("car frame",(.025,.033,.039),.28,.6)
    mat("car glass",(.018,.045,.06),.12,.42)
    mat("alloy",(.42,.45,.48),.22,.85)
    mat("rubber",(.012,.014,.016),.88)
    mat("headlamp",(.78,.68,.47),.2,emission=2.8)
    mat("tail lamp",(.38,.025,.018),.25,.1)
    mat("bus",(.10,.24,.28),.32,.28)
    mat("wood",(.16,.11,.075),.62,noise=100)
    mat("curtain",(.18,.17,.15),.9,noise=180)
    mat("ceramic",(.40,.36,.30),.22)
    mat("brick",(.15,.10,.08),.87,noise=65,bump=.12)
    mat("mortar",(.20,.17,.14),.94)
    mat("green glass",(.025,.18,.10),.08,.2)
    mat("glass shard",(.28,.42,.39),.11,.35)
    mat("aged plaster",(.26,.24,.20),.93,noise=55,bump=.14)
    mat("press",(.045,.06,.068),.38,.72,noise=90)
    mat("kettle",(.30,.32,.33),.24,.82)
    mat("pen",(.035,.065,.09),.3,.42)
    mat("pouch",(.17,.21,.17),.92,noise=160)
    mat("chair",(.07,.09,.10),.62,.12)
    mat("chalk",(.78,.75,.66),.95)

def build(out):
    scene=bpy.context.scene
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    materials()
    scene.render.engine="CYCLES"; scene.cycles.device="CPU"; scene.cycles.samples=20; scene.cycles.use_denoising=True
    scene.render.resolution_x=WIDTH; scene.render.resolution_y=HEIGHT; scene.render.resolution_percentage=100
    scene.render.fps=FPS; scene.frame_start=1; scene.frame_end=TOTAL_FRAMES
    scene.render.image_settings.file_format="PNG"; scene.render.image_settings.color_mode="RGB"; scene.render.film_transparent=False
    scene.render.use_motion_blur=True; scene.render.motion_blur_shutter=.3
    try: scene.view_settings.view_transform="AgX"
    except Exception: scene.view_settings.view_transform="Filmic"
    if scene.world and scene.world.use_nodes:
        bg=scene.world.node_tree.nodes.get("Background"); bg.inputs["Color"].default_value=(.055,.068,.085,1); bg.inputs["Strength"].default_value=.35
    clerk_center=0
    registry(clerk_center); corridor(80); threshold(120)
    kaylen_city=city(160); kaylen_room=interior(200); kaylen_mem=memory_street(240); kaylen_phone=interior(280)
    # Exterior sign and facade of the disused print shop.
    floor("Printshop exterior",320,0,16,10,MATS["asphalt"])
    box("Printshop facade",(320,4,2.5),(12,.5,5),MATS["aged plaster"],.07)
    box("Printshop entrance door",(320,3.72,1.55),(2.1,.13,3.1),MATS["door"],.04)
    for x in (316.7,323.3): box("Painted storefront window",(x,3.70,2.6),(3,.08,2),MATS["black glass"],.02)
    text("Printshop facade sign","OLD CITY PRINT WORKS",(320,3.62,4.1),.24,MATS["gold"])
    for c in (360,400,440): printshop(c)
    # People are individual, smooth 3D concept models. All unsourced likeness details remain provisional.
    kaylen_print=character("Kaylen Atlee — approach",(320,-2,0),(.37,.20,.15),(.022,.018,.016),(.09,.14,.19),(.075,.085,.10),"short",.99)
    crew=[
      ("Kaylen Atlee — crew",(357.8,-.4,0),(.37,.20,.15),(.022,.018,.016),(.09,.14,.19),(.075,.085,.10),"short",.99),
      ("Kesh Ayo",(354.3,.6,0),(.34,.19,.14),(.03,.022,.018),(.14,.18,.16),(.08,.09,.10),"short",1),
      ("Amel Zori",(365.3,.6,0),(.43,.25,.18),(.035,.03,.04),(.19,.12,.20),(.11,.10,.12),"bun",1),
      ("Juno Saye",(358.9,1.7,0),(.39,.23,.17),(.025,.02,.018),(.13,.17,.17),(.10,.10,.10),"locs",1),
      ("Biko Nare",(362.1,-.2,0),(.48,.29,.20),(.07,.04,.025),(.38,.25,.13),(.14,.13,.12),"curls",1),
      ("Tovin Bell",(356.3,1,0),(.39,.20,.14),(.025,.03,.04),(.40,.25,.12),(.13,.19,.28),"short",.96),
      ("Lark Temba",(364.1,1.3,0),(.33,.19,.14),(.035,.03,.03),(.15,.15,.19),(.12,.13,.16),"locs",1),
      ("Rasha Deni",(355,-1.1,0),(.41,.24,.18),(.025,.02,.018),(.30,.13,.15),(.11,.10,.11),"bun",1),
      ("Sefu Malk",(365.8,-1.1,0),(.35,.20,.15),(.035,.03,.025),(.16,.17,.14),(.09,.10,.10),"short",1),
    ]
    for values in crew:
        nm,pos,sk,ha,jk,tr,hs,h=values; character(nm,pos,sk,ha,jk,tr,hs,h)
    character("Kaylen Atlee — treatment",(398.9,-.4,0),(.37,.20,.15),(.022,.018,.016),(.09,.14,.19),(.075,.085,.10),"short",.99)
    character("Juno Saye — treatment",(400.65,-.2,0),(.39,.23,.17),(.025,.02,.018),(.13,.17,.17),(.10,.10,.10),"locs",1)
    character("Eamon Voss",(440.2,3,0),(.42,.25,.18),(.018,.016,.014),(.035,.045,.06),(.07,.08,.09),"short",1.02)
    character("Lark Temba — doorway",(444.5,2.5,0),(.33,.19,.14),(.035,.03,.03),(.15,.15,.19),(.12,.13,.16),"locs",1)
    character("Biko Nare — doorway",(437,0,0),(.48,.29,.20),(.07,.04,.025),(.38,.25,.13),(.14,.13,.12),"curls",1)
    character("Amel Zori — doorway",(439.8,0,0),(.43,.25,.18),(.035,.03,.04),(.19,.12,.20),(.11,.10,.12),"bun",1)
    animate(kaylen_city,FPS*100+1,FPS*125,(159,-1.6,0),(161.4,-1.6,0))
    animate(kaylen_print,FPS*200+1,FPS*225,(318,-2,0),(320,-2,0))
    for c,p in ((0,1450),(40,900),(80,1200),(120,1050),(160,1800),(200,850),(240,1000),(280,900),(320,950),(360,900),(400,900),(440,1100)): light_set(c,p)
    point("City display glow",(150,-6,3),160,(.25,.55,.75),1.8)
    point("Print press task light",(354,-1,3.1),120,(1,.55,.28),.8)
    # Twelve 25-second shots, joined with camera markers for exact, clean edits.
    shots=[
      (0,(0,-15,7.2),(0,0,2.2),38,(0,1.2,-.4)),
      (40,(38.2,-4.2,2),(40,0,1.05),78,(.55,.05,0)),
      (80,(80,-14,2.8),(80,2,2.2),42,(0,2.5,0)),
      (120,(120,-7,2.3),(120,0,1),58,(.2,.2,0)),
      (160,(160,-22,7.5),(160,1,2),30,(2.4,1.8,-.6)),
      (200,(198,-7,2.6),(200,-.2,1.45),55,(.3,.7,0)),
      (240,(239,-5,1.1),(239,-.8,.12),84,(.4,.35,0)),
      (280,(280,-4.5,1.6),(280,-.3,1),80,(.25,.1,0)),
      (320,(320,-12,3),(320,2.8,2.1),45,(.4,1,0)),
      (360,(360,-15,5),(360,.6,1.6),38,(.45,1.1,-.15)),
      (400,(397.5,-6.2,2.35),(400,-.1,1.65),72,(.25,.2,0)),
      (440,(440,-13,3),(440,1.2,1.7),45,(.2,.9,-.1)),
    ]
    for i,(c,loc,target,lens,travel) in enumerate(shots):
        f0=i*SHOT_SECONDS*FPS+1; f1=(i+1)*SHOT_SECONDS*FPS
        cam=camera("Pilot camera "+str(i+1),loc,target,lens)
        cam.keyframe_insert(data_path="location",frame=f0)
        cam.location=(loc[0]+travel[0],loc[1]+travel[1],loc[2]+travel[2]); cam.keyframe_insert(data_path="location",frame=f1)
        marker=scene.timeline_markers.new("SHOT "+str(i+1).zfill(2),frame=f0); marker.camera=cam
    scene.camera=bpy.data.objects.get("Pilot camera 1")
    scene.render.threads_mode="FIXED"; scene.render.threads=2
    scene["project"]="BROWN Book One — five-minute visual pilot"
    scene["status"]="DRAFT PILOT RENDER — visual approval required"
    scene["resolution"]="1280x720"; scene["frame_rate"]=FPS; scene["frame_count"]=TOTAL_FRAMES
    scene["render_engine"]="Cycles CPU; 20 samples; denoising"
    scene["asset_note"]="Procedural realistic-leaning concept assets. Not final approved character likenesses."
    out.mkdir(parents=True,exist_ok=True)
    blend=out/"BROWN_Five_Minute_Pilot.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    still=out/"build_still"; still.mkdir(parents=True,exist_ok=True)
    scene.frame_set(1); scene.render.filepath=str(still/"pilot_frame_000001.png")
    bpy.ops.render.render(write_still=True)
    report={"status":"BUILT_NOT_VISUALLY_APPROVED","runtime_seconds":300,"frames":7200,"fps":24,
            "resolution":[1280,720],"engine":"CYCLES_CPU","samples":20,"object_count":len(bpy.data.objects),
            "characters":"11 named or anonymous source-referenced concept models; appearance still provisional",
            "sets":["registry hall","records desk","service corridor","access checkpoint","Vesper street","unspecified interior","memory pavement","print shop exterior","print shop interior"],
            "vehicles":["taxi sedan","sedan","public transit bus"],"blend_file":str(blend)}
    (out/"pilot_build_report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))

def render_part(out,segment):
    if segment not in (1,2,3,4,5): raise ValueError("segment must be 1..5")
    scene=bpy.context.scene; scene.render.engine="CYCLES"; scene.cycles.device="CPU"
    scene.cycles.samples=20; scene.cycles.use_denoising=True
    scene.render.resolution_x=WIDTH; scene.render.resolution_y=HEIGHT; scene.render.resolution_percentage=100
    scene.render.fps=FPS; scene.render.image_settings.file_format="PNG"; scene.render.image_settings.color_mode="RGB"
    start=(segment-1)*SEGMENT_SECONDS*FPS+1; end=segment*SEGMENT_SECONDS*FPS
    frames=out/"frames"; frames.mkdir(parents=True,exist_ok=True)
    scene.frame_start=start; scene.frame_end=end; scene.render.filepath=str(frames/"frame_")
    scene.render.image_settings.color_depth="8"; scene.render.threads_mode="FIXED"; scene.render.threads=2
    scene.frame_set(start)
    print("Render segment",segment,"frames",start,"-",end,"at 1280x720 24 fps")
    bpy.ops.render.render(animation=True)
    print("Segment",segment,"render finished")

def main():
    a=get_args(); out=Path(a.output_dir).resolve(); out.mkdir(parents=True,exist_ok=True)
    if a.mode=="build": build(out)
    else: render_part(out,a.segment)

if __name__=="__main__": main()
