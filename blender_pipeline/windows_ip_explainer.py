#!/usr/bin/env python3
"""Cinematic continuously animated 90-second Windows IP Privacy explainer."""
import bpy, math, os, sys, json, argparse, subprocess, random
from mathutils import Vector

FPS,DURATION,WIDTH,HEIGHT=30,90,1080,1920
TOTAL_FRAMES=FPS*DURATION
SEGMENT_FRAMES=15*FPS
SHOT_FRAMES=9*FPS
SPACING=30.0
OUT_NAME="FrameForge_Windows_IP_Privacy_90s_AAA"

PAL={
"void":(0.004,0.010,0.024,1),"floor":(0.010,0.025,0.050,1),
"panel":(0.018,0.055,0.090,1),"panel2":(0.028,0.095,0.135,1),
"steel":(0.12,0.19,0.25,1),"white":(0.78,0.90,0.96,1),
"muted":(0.25,0.43,0.55,1),"cyan":(0.015,0.72,1.0,1),
"blue":(0.025,0.22,0.88,1),"teal":(0.015,0.54,0.48,1),
"amber":(1.0,0.40,0.07,1),"red":(0.95,0.055,0.09,1),
"green":(0.08,0.88,0.43,1),"grid":(0.012,0.10,0.17,1),
"dust":(0.12,0.50,0.82,1),"planet":(0.008,0.085,0.20,1),
"cloth":(0.012,0.022,0.038,1),"cloth2":(0.025,0.055,0.08,1),
"rubber":(0.005,0.008,0.012,1)
}
SHOTS=[
("YOUR IP IS YOUR PUBLIC RETURN ADDRESS","A route identifier for your internet connection"),
("IT CAN REVEAL YOUR APPROXIMATE REGION","It does not directly reveal your exact home address"),
("WINDOWS VPN SETTINGS ARE NOT A VPN SERVICE","A connection profile still needs a VPN provider and server"),
("MEET EDGE SECURE NETWORK","A browser privacy feature with VPN-style protection"),
("OPEN SECURE NETWORK","Edge menu  >  More tools  >  Secure Network"),
("SIGN IN AND ENABLE PROTECTION","Use a personal Microsoft account where supported"),
("CHOOSE YOUR PROTECTION MODE","Optimized  |  Select Sites  |  All Sites"),
("CHECK FOR THE SHIELD","The shield indicates Secure Network is active"),
("COMPARE YOUR PUBLIC IP","Check before and after on a trusted IP-check site"),
("KNOW THE LIMITS","5 GB monthly allowance  |  Edge traffic  |  Not anonymity")
]

def args_parse():
    a=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("audit","render"),default="audit")
    p.add_argument("--segment-index",type=int,default=0)
    p.add_argument("--output-dir",default="output/windows_ip_explainer")
    return p.parse_args(a)

def safe_set(o,k,v):
    try: setattr(o,k,v)
    except Exception: pass

def material(name,color,metal=0.1,rough=0.4,glow=0):
    m=bpy.data.materials.new(name); m.diffuse_color=color; m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    if bs:
        bs.inputs["Base Color"].default_value=color
        bs.inputs["Metallic"].default_value=metal
        bs.inputs["Roughness"].default_value=rough
        for n in ("Emission","Emission Color"):
            if n in bs.inputs: bs.inputs[n].default_value=color
        if "Emission Strength" in bs.inputs: bs.inputs["Emission Strength"].default_value=glow
    return m

def attach(o,m):
    if m:o.data.materials.append(m)
    return o

def bevel(o,w=0.05,seg=4):
    if w>0:
        b=o.modifiers.new("Precision edge bevel","BEVEL"); b.width=w; b.segments=seg
        try:o.modifiers.new("Weighted normals","WEIGHTED_NORMAL")
        except Exception:pass
    return o

def box(n,loc,size,m,w=0.06):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=n
    o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    attach(o,m);bevel(o,w);return o

def sphere(n,loc,scale,m,seg=32,rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,radius=1,location=loc)
    o=bpy.context.object;o.name=n;o.scale=scale;attach(o,m)
    for p in o.data.polygons:p.use_smooth=True
    return o

def ico(n,loc,scale,m,sub=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub,radius=1,location=loc)
    o=bpy.context.object;o.name=n;o.scale=scale;attach(o,m);return o

def ring(n,loc,r,t,m,rot=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=r,minor_radius=t,major_segments=64,minor_segments=12,location=loc,rotation=rot)
    o=bpy.context.object;o.name=n;attach(o,m)
    for p in o.data.polygons:p.use_smooth=True
    return o

def line(n,pts,w,m,cyclic=False):
    d=bpy.data.curves.new(n,"CURVE");d.dimensions="3D";d.resolution_u=12;d.bevel_depth=w;d.bevel_resolution=3
    s=d.splines.new("POLY");s.points.add(len(pts)-1)
    for p,v in zip(s.points,pts):p.co=(v[0],v[1],v[2],1)
    s.use_cyclic_u=cyclic
    o=bpy.data.objects.new(n,d);bpy.context.collection.objects.link(o);attach(o,m);return o

def text(n,body,loc,size,m,align="CENTER"):
    d=bpy.data.curves.new(n,"FONT");d.body=body;d.size=size;d.align_x=align;d.align_y="CENTER"
    d.extrude=0.002;d.bevel_depth=0.0006
    o=bpy.data.objects.new(n,d);bpy.context.collection.objects.link(o)
    o.location=loc;o.rotation_euler=(math.pi/2,0,0);attach(o,m);return o

def between(n,a,b,r,m):
    a,b=Vector(a),Vector(b);v=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=v.length,location=(a+b)*0.5)
    o=bpy.context.object;o.name=n;o.rotation_euler=v.to_track_quat("Z","Y").to_euler()
    attach(o,m);bevel(o,r*0.18,3);return o

def motion(o,seed,strength=1.0):
    rng=random.Random(seed);loc=tuple(o.location);rot=tuple(o.rotation_euler);sc=tuple(o.scale)
    typ=getattr(o,"type","");large=max(abs(v) for v in sc)>5
    amp=(0.012 if typ=="FONT" else (0.008 if large else 0.035))*strength
    f=rng.uniform(0.010,0.026);p=rng.uniform(0,math.tau)
    for ax,base,mul in zip(range(3),loc,(1,0.65,1.15)):
        try:
            c=o.driver_add("location",ax);c.driver.expression="%.7f+%.7f*sin(frame*%.7f+%.7f)"%(base,amp*mul,f,p+ax*1.7)
        except Exception:pass
    ra=0.003 if typ=="FONT" or large else 0.012
    for ax,base in zip(range(3),rot):
        try:
            c=o.driver_add("rotation_euler",ax);c.driver.expression="%.7f+%.7f*sin(frame*%.7f+%.7f)"%(base,ra*(ax+1)*strength,f*0.83,p+ax*2.1)
        except Exception:pass
    for ax,base in zip(range(3),sc):
        try:
            c=o.driver_add("scale",ax);c.driver.expression="%.7f*(1+%.7f*sin(frame*%.7f+%.7f))"%(base,0.0025*strength,f*1.31,p+ax)
        except Exception:pass

def card(n,x,y,z,title,sub,M,width=7):
    box(n+" chassis",(x,y,z),(width,0.38,3.55),M["panel"],0.17)
    box(n+" edge",(x-width/2+0.1,y-0.21,z),(0.08,0.035,2.95),M["cyan"],0.02)
    text(n+" heading",title,(x,y-0.23,z+0.64),0.42,M["white"])
    text(n+" sub",sub,(x,y-0.23,z-0.25),0.21,M["muted"])

def operator(x,M):
    y=-0.3
    for side in (-1,1):
        q=x+side*0.25
        between("Operator leg",(q,y,0.15),(q+side*0.04,y,1.18),0.17,M["cloth"])
        box("Operator boot",(q+side*0.04,y-0.17,0.13),(0.4,0.62,0.22),M["rubber"],0.08)
    sphere("Operator torso",(x,y,2.0),(0.72,0.38,0.95),M["cloth"])
    sphere("Operator shoulders",(x,y+0.01,2.48),(0.79,0.4,0.48),M["cloth2"])
    sphere("Operator hood",(x,y,3.22),(0.53,0.43,0.64),M["cloth2"])
    sphere("Operator mask",(x,y-0.285,3.18),(0.36,0.12,0.4),M["void"])
    box("Operator visor",(x,y-0.40,3.27),(0.54,0.055,0.105),M["cyan"],0.04)
    box("Operator chest module",(x-0.22,y-0.365,2.12),(0.28,0.07,0.43),M["steel"],0.05)
    box("Operator chest light",(x-0.22,y-0.41,2.20),(0.12,0.025,0.055),M["green"],0.01)
    for side in (-1,1):
        a=(x+side*0.70,y,2.48);b=(x+side*0.88,y-0.06,1.85);c=(x+side*0.65,y-0.33,1.40)
        between("Operator sleeve",a,b,0.22,M["cloth2"]);between("Operator forearm",b,c,0.15,M["cloth"])
        sphere("Operator glove",c,(0.2,0.16,0.18),M["rubber"])
    box("Operator back rig",(x,y+0.34,2.2),(0.46,0.3,0.82),M["steel"],0.08)
    ring("Operator status ring",(x,y+0.16,2.46),0.18,0.025,M["amber"],(math.pi/2,0,0))

def hud_stage(i,M):
    x=i*SPACING
    box("Stage floor",(x,0,-0.92),(13,24,0.55),M["floor"],0.18)
    for j in range(-6,7):line("Floor longitudinal grid",[(x+j,-10,-0.635),(x+j*0.82,10,-0.635)],0.006,M["grid"])
    for j in range(-9,11,2):line("Floor cross grid",[(x-6.3,j,-0.63),(x+6.3,j,-0.63)],0.006,M["grid"])
    for sx in (-6,6):box("Floor edge light",(x+sx,0,-0.58),(0.035,18,0.03),M["cyan"],0.01)
    rng=random.Random(400+i)
    for _ in range(18):
        p=(x+rng.uniform(-5.7,5.7),rng.uniform(-1,8.5),rng.uniform(0.7,13.5))
        s=rng.uniform(0.018,0.05);ico("Animated dust particle",p,(s,s,s),M["dust"],1)
    text("Kicker","FRAMEFORGE / PRIVACY FIELD GUIDE / %02d"%(i+1),(x,-7.8,15),0.17,M["cyan"])
    h,sub=SHOTS[i];size=min(0.42,9.0/(max(1,len(h))*0.59))
    text("Shot title",h,(x,-7.95,13.65),size,M["white"])
    text("Shot subtitle",sub,(x,-7.96,12.82),0.21,M["muted"])
    for side in (-1,1):
        box("Vertical light rail",(x+side*5.9,0.3,6.3),(0.045,0.06,10.8),M["grid"],0.02)
        for k in range(4):sphere("Rail marker",(x+side*5.9,-0.1,2.1+k*2.7),(0.08,0.06,0.08),M["cyan"] if side<0 else M["amber"],16,8)
    if i in (0,1):
        sphere("Holographic earth",(x,0.25,6.2),(2.15,2.15,2.15),M["planet"],64,40)
        for lat in (-60,-30,0,30,60):
            r=2.17*math.cos(math.radians(lat));z=6.2+2.17*math.sin(math.radians(lat))
            pts=[(x+r*math.cos(a),0.18+r*math.sin(a),z) for a in [math.tau*k/96 for k in range(96)]]
            line("Globe latitude",pts,0.012,M["grid"],True)
        for lon in range(0,180,30):
            a=math.radians(lon);pts=[]
            for k in range(65):
                t=-math.pi/2+math.pi*k/64
                pts.append((x+2.18*math.cos(t)*math.cos(a),0.18+2.18*math.cos(t)*math.sin(a),6.2+2.18*math.sin(t)))
            line("Globe longitude",pts,0.012,M["grid"])
        ring("Globe orbital cyan",(x,0.2,6.2),2.75,0.028,M["cyan"],(math.radians(68),0,math.radians(26)))
        ring("Globe orbital amber",(x,0.2,6.2),2.95,0.018,M["amber"],(math.radians(18),math.radians(66),0))
        if i==0:
            card("Public IP",x-3.25,-2.3,4,"PUBLIC IP","203.0.113.42 / EXAMPLE",M,3)
            box("Source device",(x+3.6,-1.5,2.2),(1.8,0.18,1.1),M["steel"],0.12)
            box("Source display",(x+3.6,-1.62,2.26),(1.55,0.025,0.82),M["cyan"],0.06)
            line("Internet route",[(x+2.8,-1.5,2.8),(x+1.8,-1.7,3.8),(x+0.65,-1.2,5),(x-0.4,-0.65,5.7)],0.035,M["amber"])
            for j in range(5):ico("Data packet",(x+2.5-j*0.6,-1.75,3+j*0.5),(0.11,0.11,0.11),M["amber"],2)
            operator(x-4.2,M)
        else:
            for r in (0.6,1.0,1.45,1.9):ring("Region scan ring",(x+0.65,-1.7,5.9),r,0.025,M["amber"],(math.pi/2,0,0))
            between("Map pin body",(x+0.65,-1.8,6),(x+0.65,-1.8,7.45),0.13,M["red"])
            sphere("Map pin head",(x+0.65,-1.82,7.6),(0.35,0.22,0.35),M["red"])
            text("Region note","APPROXIMATE REGION",(x,-2.3,2),0.33,M["amber"])
            text("Region caveat","NOT A STREET-LEVEL ADDRESS",(x,-2.35,1.4),0.18,M["muted"])
    elif i==2:
        card("Windows VPN profile",x,-0.6,7,"WINDOWS VPN SETTINGS","A place to configure a connection",M,7.2)
        for k,(t,v) in enumerate((("VPN PROVIDER","Windows built-in"),("SERVER NAME","Supplied by your VPN provider"),("SIGN-IN","Provider account or certificate"))):
            z=7.5-k*1.12;text("VPN field title",t,(x-2.7,-0.86,z),0.17,M["cyan"],"LEFT")
            box("VPN input",(x+0.75,-0.83,z-0.34),(5,0.08,0.47),M["void"],0.07)
            text("VPN field value",v,(x+0.75,-0.91,z-0.34),0.18,M["white"])
        ring("Unconnected VPN port",(x,0,2.1),0.92,0.09,M["red"],(math.pi/2,0,0))
        ico("Endpoint core",(x,-0.1,2.1),(0.3,0.22,0.3),M["red"],2)
        text("VPN explanation","A PROFILE IS NOT THE SERVICE",(x,-0.5,0.8),0.22,M["amber"])
    elif i in (3,4):
        box("Browser chassis",(x,0.6,6.3),(7.1,0.36,5.7),M["steel"],0.2)
        box("Browser glass",(x,0.395,6.3),(6.85,0.10,5.42),M["panel"],0.14)
        box("Browser top bar",(x,0.31,8.57),(6.72,0.045,0.52),M["panel2"],0.05)
        for j,c in enumerate((M["red"],M["amber"],M["green"])):sphere("Browser control",(x-3+j*0.24,0.24,8.57),(0.055,0.04,0.055),c,16,8)
        box("Address bar",(x+0.15,0.24,8.57),(4.7,0.035,0.2),M["void"],0.06)
        for j in range(4):box("Browser content tile",(x-1.75+(j%2)*3.1,0.24,7.05-(j//2)*1.25),(2.55,0.035,0.88),M["panel2"],0.07)
        if i==3:
            for r in (2,2.45,2.9):ring("Secure Network tunnel",(x,-1.7,6),r,0.045,M["cyan"],(math.pi/2,0,0))
            sphere("Shield core",(x,-2.05,6.15),(1.12,0.2,1.28),M["teal"])
            pts=[(x,-2.31,7.15),(x+0.78,-2.31,6.85),(x+0.62,-2.31,5.65),(x,-2.31,5.08),(x-0.62,-2.31,5.65),(x-0.78,-2.31,6.85)]
            line("Secure shield border",pts,0.09,M["cyan"],True)
            line("Secure shield check",[(x-0.4,-2.4,6.15),(x-0.08,-2.42,5.82),(x+0.48,-2.42,6.53)],0.075,M["white"])
            text("Edge security label","SECURE NETWORK",(x,-2,3.35),0.3,M["white"])
        else:
            box("Edge menu dropdown",(x+1.55,-1.75,5.3),(3,0.20,4.55),M["panel2"],0.12)
            for k,t in enumerate(("NEW TAB","HISTORY","DOWNLOADS","MORE TOOLS","SECURE NETWORK  >")):
                z=7-k*0.76
                if k==4:box("Selected menu row",(x+1.55,-1.89,z),(2.68,0.055,0.60),M["blue"],0.05)
                text("Menu entry",t,(x+1.55,-1.99,z),0.18,M["white"] if k==4 else M["muted"])
            ring("Cursor ripple",(x+2.45,-2.2,3.96),0.23,0.045,M["amber"],(math.pi/2,0,0))
            line("Cursor pointer",[(x+2.25,-2.25,4.32),(x+2.08,-2.25,3.84),(x+2.43,-2.25,3.98),(x+2.25,-2.25,4.32)],0.035,M["white"],True)
    elif i==5:
        card("Account panel",x,-0.5,7.1,"SIGN IN TO CONTINUE","Use a personal Microsoft account",M,7.3)
        sphere("Account avatar",(x-2.4,-1.15,7),(0.62,0.18,0.62),M["blue"])
        sphere("Avatar head",(x-2.4,-1.42,7.12),(0.23,0.1,0.23),M["white"])
        sphere("Avatar shoulders",(x-2.4,-1.42,6.72),(0.4,0.1,0.23),M["cyan"])
        for j,t in enumerate(("ACCOUNT","PASSWORD")):
            z=5.75-j*0.87;text("Account label",t,(x-2,-1.2,z),0.16,M["cyan"],"LEFT")
            box("Account field",(x+0.65,-1.25,z-0.34),(4.7,0.08,0.43),M["void"],0.06)
        box("Protection toggle",(x+1.4,-1.45,3.55),(2.1,0.15,0.78),M["green"],0.3)
        sphere("Toggle thumb",(x+2,-1.58,3.55),(0.31,0.18,0.31),M["white"])
        text("Protection enabled","PROTECTION ENABLED",(x,-1.6,2.35),0.26,M["green"])
        operator(x-4.6,M)
    elif i==6:
        modes=[("OPTIMIZED","Automatic when needed",M["green"]),("SELECT SITES","Choose websites",M["blue"]),("ALL SITES","Broader Edge coverage",M["cyan"])]
        for k,(t,d,c) in enumerate(modes):
            xx=x+(k-1)*3.35
            box("Protection mode card",(xx,-0.8,6),(2.85,0.38,4.8),M["panel2"],0.16)
            box("Mode header light",(xx,-1.04,8),(2.45,0.05,0.13),c,0.03)
            ring("Mode hologram",(xx,-1.1,6.5),0.72,0.04,c,(math.pi/2,0,0))
            ico("Mode symbol",(xx,-1.22,6.5),(0.25,0.16,0.25),c,2)
            text("Mode name",t,(xx,-1.17,5.35),0.21,M["white"])
            text("Mode detail",d,(xx,-1.18,4.72),0.15,M["muted"])
        text("Mode recommendation","START WITH OPTIMIZED",(x,-1.5,2.3),0.25,M["green"])
    elif i==7:
        for j,r in enumerate((2.35,2.85,3.35)):ring("Shield halo",(x,0.15,6.1),r,0.045,M["cyan"] if j!=1 else M["amber"],(math.pi/2,0,0))
        sphere("Active shield core",(x,-1.65,6.15),(1.55,0.32,1.75),M["blue"])
        pts=[(x,-2.02,7.72),(x+1,-2.02,7.28),(x+0.82,-2.02,5.65),(x,-2.02,4.6),(x-0.82,-2.02,5.65),(x-1,-2.02,7.28)]
        line("Active shield outline",pts,0.105,M["cyan"],True)
        line("Shield check",[(x-0.53,-2.17,6.25),(x-0.12,-2.2,5.82),(x+0.58,-2.2,6.72)],0.105,M["white"])
        for j in range(7):ico("Protected packet",(x-3.3+j*1.1,-1.9,4+0.4*(j%3)),(0.1,0.1,0.1),M["amber"],2)
        text("Shield status","SHIELD ACTIVE",(x,-1,2.45),0.3,M["green"]);operator(x-4.3,M)
    elif i==8:
        for k,(h,ip,c) in enumerate((("BEFORE","203.0.113.42",M["amber"]),("AFTER","198.51.100.18",M["green"]))):
            xx=x+(k-0.5)*3.8
            box("IP comparison terminal",(xx,-0.8,6.4),(3.4,0.34,3.6),M["panel2"],0.14)
            box("IP card accent",(xx,-1.04,7.55),(3.12,0.06,0.16),c,0.03)
            text("IP comparison heading",h,(xx,-1.13,7),0.28,c)
            text("IP value",ip,(xx,-1.14,6.18),0.22,M["white"])
            text("IP category","PUBLIC ADDRESS",(xx,-1.15,5.6),0.15,M["muted"])
        line("IP comparison route",[(x-1.7,-1.65,4.2),(x-0.7,-1.85,4.6),(x+0.7,-1.85,4.6),(x+1.7,-1.65,4.2)],0.05,M["cyan"])
        for j in range(5):ico("IP change packet",(x-1.4+j*0.7,-1.9,4.2+0.3*math.sin(j)),(0.09,0.09,0.09),M["cyan"],2)
        text("IP example disclaimer","ILLUSTRATIVE EXAMPLE ADDRESSES",(x,-1.1,2.7),0.2,M["muted"])
    elif i==9:
        card("Limits panel",x,-0.6,7.15,"PRIVACY HAS BOUNDARIES","Useful protection, not complete anonymity",M,7.6)
        blocks=[("5 GB","MONTHLY ALLOWANCE",M["amber"]),("EDGE","BROWSER TRAFFIC",M["cyan"]),("NOT ANON","NO TOTAL ANONYMITY",M["red"])]
        for k,(big,small,c) in enumerate(blocks):
            xx=x+(k-1)*2.55
            box("Limit terminal",(xx,-1,5.2),(2.25,0.34,2.6),M["panel2"],0.14)
            ring("Limit gauge",(xx,-1.32,5.85),0.53,0.055,c,(math.pi/2,0,0))
            text("Limit heading",big,(xx,-1.36,5.8),0.34,c)
            text("Limit description",small,(xx,-1.38,4.65),0.15,M["white"])
        for j in range(10):box("Allowance meter",(x-2.7+j*0.6,-1,2.65),(0.48,0.13,0.18),M["cyan"] if j<5 else M["steel"],0.03)
        text("Availability caveat","AVAILABILITY AND ALLOWANCE CAN VARY",(x,-1.25,1.65),0.18,M["amber"])

def camera_rig(scene):
    bpy.ops.object.empty_add(type="PLAIN_AXES",location=(0,-24,10.6));root=bpy.context.object;root.name="Cinematic camera rail"
    bpy.ops.object.camera_add(location=(0,0,0));cam=bpy.context.object;cam.name="AAA vertical camera"
    cam.parent=root;cam.location=(0,0,0);cam.data.type="ORTHO";cam.data.ortho_scale=17.5;scene.camera=cam
    bpy.ops.object.empty_add(type="SPHERE",location=(0,0,6.1));target=bpy.context.object
    target.name="Animated camera target";target.empty_display_size=0.01
    c=cam.constraints.new(type="TRACK_TO");c.target=target;c.track_axis="TRACK_NEGATIVE_Z";c.up_axis="UP_Z"
    for i in range(10):
        st=i*SHOT_FRAMES+1;cx=i*SPACING;last=1.0 if i<9 else 0.0
        for frame,travel,bob in ((st,0,0),(st+110,0,0.14),(st+220,0,-0.08),(min(st+269,TOTAL_FRAMES),last,0)):
            root.location=(cx+SPACING*travel,-24.5+0.30*math.sin(i+frame*0.014),10.2+0.25*math.sin(frame*0.025+i))
            root.keyframe_insert(data_path="location",frame=frame)
            target.location=(cx+SPACING*travel,-0.2,6+bob);target.keyframe_insert(data_path="location",frame=frame)
    # Blender 5 uses layered actions; retain its default smooth Bezier interpolation.
    for ax,amp,freq,phase in ((1,0.09,0.021,0),(2,0.07,0.017,1.1)):
        fc=root.driver_add("location",ax);fc.driver.expression="%.6f*sin(frame*%.6f+%.4f)"%(amp,freq,phase)
    for ax,amp,freq,phase in ((0,0.015,0.019,0.3),(1,0.018,0.016,1.8),(2,0.012,0.022,2.4)):
        fc=cam.driver_add("rotation_euler",ax);fc.driver.expression="%.6f*sin(frame*%.6f+%.4f)"%(amp,freq,phase)
    return cam,root,target

def compositor(scene):
    scene.use_nodes=True;nt=scene.node_tree;nt.nodes.clear()
    rl=nt.nodes.new("CompositorNodeRLayers");g=nt.nodes.new("CompositorNodeGlare")
    g.glare_type="FOG_GLOW";safe_set(g,"quality","HIGH");safe_set(g,"threshold",1.25);safe_set(g,"size",7)
    out=nt.nodes.new("CompositorNodeComposite")
    nt.links.new(rl.outputs["Image"],g.inputs["Image"]);nt.links.new(g.outputs["Image"],out.inputs["Image"])

def build_scene():
    bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
    M={k:material(k,v,0.7 if k in ("steel","panel","panel2") else 0.12,
        0.28 if k in ("steel","panel","panel2") else 0.38,
        1.4 if k in ("cyan","amber","green","red","blue") else 0) for k,v in PAL.items()}
    world=bpy.data.worlds.new("Dark cinematic world") if not bpy.data.worlds else bpy.data.worlds[0]
    scene=bpy.context.scene;scene.world=world;world.use_nodes=True
    world.node_tree.nodes["Background"].inputs["Color"].default_value=PAL["void"]
    world.node_tree.nodes["Background"].inputs["Strength"].default_value=0.28
    lights=[
      ("Overhead softbox",(0,-7,18),2400,11,(0.40,0.72,1)),
      ("Cyan side rim",(-8,1,9),1800,7,(0.02,0.55,1)),
      ("Amber edge",(8,5,11),1500,6,(1,0.30,0.08)),
      ("Front fill",(0,-13,8),850,8,(0.42,0.65,0.88))]
    for n,loc,power,size,color in lights:
        bpy.ops.object.light_add(type="AREA",location=loc);o=bpy.context.object
        o.name=n;o.data.energy=power;o.data.shape="DISK";o.data.size=size;o.data.color=color
        o.rotation_euler=(math.radians(20),0,math.radians(20))
    for i in range(10):hud_stage(i,M)
    cam,root,target=camera_rig(scene)
    for idx,o in enumerate(list(bpy.data.objects)):
        if o.name not in {cam.name,root.name,target.name}:motion(o,1000+idx,0.55 if o.type=="LIGHT" else 1.0)
    for o in bpy.data.objects:
        if o.type=="LIGHT":
            try:
                fc=o.data.driver_add("energy");phase=(sum(ord(ch) for ch in o.name)%100)/17
                fc.driver.expression="%.3f*(1+0.08*sin(frame*0.018+%.3f))"%(o.data.energy,phase)
            except Exception:pass
    scene.frame_start=1;scene.frame_end=TOTAL_FRAMES;scene.render.engine="BLENDER_EEVEE"
    scene.render.resolution_x=WIDTH;scene.render.resolution_y=HEIGHT;scene.render.resolution_percentage=100
    scene.render.fps=FPS;scene.render.image_settings.color_mode="RGB"
    scene.render.image_settings.file_format="PNG";scene.render.image_settings.color_depth="8"
    scene.render.film_transparent=False;scene.render.use_file_extension=True
    scene.view_settings.view_transform="Standard";safe_set(scene.view_settings,"look","Medium High Contrast")
    safe_set(scene.view_settings,"exposure",0);safe_set(scene.view_settings,"gamma",1)
    if hasattr(scene,"eevee"):
        safe_set(scene.eevee,"taa_render_samples",64);safe_set(scene.eevee,"use_gtao",True)
        safe_set(scene.eevee,"gtao_distance",3);safe_set(scene.eevee,"gtao_factor",1.25)
        safe_set(scene.eevee,"use_soft_shadows",True);safe_set(scene.eevee,"use_motion_blur",True)
    safe_set(scene.render,"use_motion_blur",True);safe_set(scene.render,"motion_blur_shutter",0.35)
    compositor(scene);scene.frame_set(1);bpy.context.view_layer.update();return scene

def audit(scene,outdir):
    os.makedirs(outdir,exist_ok=True);cam=scene.camera
    for f in range(1,TOTAL_FRAMES+1):
        scene.frame_set(f);bpy.context.view_layer.update()
        if not all(math.isfinite(v) for v in tuple(cam.matrix_world.translation)):
            raise RuntimeError("Camera transform invalid at frame %d"%f)
    scene.frame_set(1);bpy.context.view_layer.update();objs=list(bpy.data.objects)
    before={o.name:(tuple(o.location),tuple(o.rotation_euler),tuple(o.scale)) for o in objs}
    scene.frame_set(2);bpy.context.view_layer.update();moved=0
    for o in objs:
        a=before[o.name];b=(tuple(o.location),tuple(o.rotation_euler),tuple(o.scale))
        if any(abs(x-y)>1e-9 for va,vb in zip(a,b) for x,y in zip(va,vb)):moved+=1
    ratio=moved/max(1,len(objs))
    if ratio<0.90:raise RuntimeError("Frame-to-frame motion audit failed: %.1f%% moved"%(ratio*100))
    scene.frame_set(1);project=os.path.join(outdir,OUT_NAME+".blend")
    bpy.ops.wm.save_as_mainfile(filepath=project)
    report={"status":"PASS","duration_seconds":DURATION,"frame_count":TOTAL_FRAMES,
      "fps":FPS,"resolution":[WIDTH,HEIGHT],"renderer":"Blender Eevee",
      "style":"Dark cinematic 3D cybersecurity motion graphics",
      "continuous_motion":"Per-object transform drivers evaluated every frame, animated camera rail/target, lights and data motes",
      "frame_to_frame_motion_audit_percent":round(ratio*100,2),"motion_blur":True,
      "eevee_samples":64,"animated_object_count":sum(1 for o in bpy.data.objects if o.animation_data),
      "camera_transform_audit":"2700 frames checked; all finite",
      "shots":[{"title":s[0],"descriptor":s[1]} for s in SHOTS],"editable_project":os.path.basename(project)}
    with open(os.path.join(outdir,"audit.json"),"w",encoding="utf-8") as f:json.dump(report,f,indent=2)
    print("AAA_AUDIT_PASS",ratio*100,"percent frame-to-frame object movement",flush=True)

def render_segment(scene,seg,outdir):
    if seg<0 or seg>5:raise ValueError("segment-index must be 0..5")
    os.makedirs(outdir,exist_ok=True);start=seg*SEGMENT_FRAMES+1;end=start+SEGMENT_FRAMES-1
    fd=os.path.join(outdir,"segment_%02d_frames"%seg);os.makedirs(fd,exist_ok=True)
    prefix=os.path.join(fd,"frame_");scene.render.filepath=prefix
    scene.render.image_settings.file_format="PNG";scene.render.image_settings.color_mode="RGB"
    scene.render.image_settings.color_depth="8";scene.render.fps=FPS
    scene.render.resolution_x=WIDTH;scene.render.resolution_y=HEIGHT;scene.render.resolution_percentage=100
    scene.frame_start=start;scene.frame_end=end;scene.frame_set(start)
    print("AAA_RENDER_START",seg,start,end,WIDTH,HEIGHT,flush=True)
    bpy.ops.render.render(animation=True)
    path=os.path.join(outdir,"segment_%02d.mp4"%seg)
    cmd=["ffmpeg","-y","-framerate",str(FPS),"-start_number",str(start),"-i",prefix+"%04d.png",
         "-frames:v",str(SEGMENT_FRAMES),"-c:v","libx264","-preset","slow","-crf","16",
         "-pix_fmt","yuv420p","-movflags","+faststart",path]
    subprocess.run(cmd,check=True)
    if not os.path.exists(path) or os.path.getsize(path)<200000:
        raise RuntimeError("Render output missing or too small: "+path)
    print("AAA_SECTION_VERIFIED",path,os.path.getsize(path),flush=True)

def main():
    a=args_parse();s=build_scene()
    if a.mode=="audit":audit(s,a.output_dir)
    else:render_segment(s,a.segment_index,a.output_dir)

if __name__=="__main__":main()
