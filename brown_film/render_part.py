import bpy, math, json, os, random, sys
from mathutils import Vector
from math import sin, pi
def arg(n,d):
 a=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
 return a[a.index(n)+1] if n in a else d
with open(arg("--config","brown_part.json"),encoding="utf8") as f: C=json.load(f)
P=int(C["part"]); random.seed(1000+P)
START_FRAME = int(arg("--start-frame", "1"))
END_FRAME = int(arg("--end-frame", "6000"))
if not (1 <= START_FRAME <= END_FRAME <= 6000):
 raise ValueError(f"Invalid frame range {START_FRAME}-{END_FRAME}; expected 1-6000")
OUT=os.environ.get("BROWN_OUTPUT",f"render/part-{P:02d}.mp4"); os.makedirs("render",exist_ok=True)
bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
def mat(n,c,r=.85):
 m=bpy.data.materials.new(n); m.diffuse_color=(*c,1); m.use_nodes=True
 m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(*c,1)
 m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value=r
 return m
M={"skin":mat("warm skin",(.40,.23,.15)),"dark":mat("deep skin",(.22,.105,.065)),"cloth":mat("charcoal cloth",(.045,.055,.07)),"coat":mat("worn coat",(.17,.19,.18)),"brown":mat("ochre",(.38,.20,.09)),"blue":mat("slate blue",(.07,.15,.22)),"stone":mat("weathered stone",(.32,.33,.31)),"glass":mat("smoked glass",(.045,.10,.13),.25),"wood":mat("dark timber",(.16,.09,.045)),"paper":mat("aged paper",(.72,.65,.48)),"white":mat("chalk",(.78,.77,.68)),"lamp":mat("warm lamp",(.95,.52,.16)),"fire":mat("ember",(.8,.12,.02))}
def cube(n,loc,dim,ma):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.name=n; o.dimensions=dim
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if ma:o.data.materials.append(ma)
 return o
def aim(o,p): o.rotation_euler=(Vector(p)-o.location).to_track_quat("-Z","Y").to_euler()
def light(n,loc,power,col,size,target):
 bpy.ops.object.light_add(type="AREA",location=loc); o=bpy.context.object;o.name=n;o.data.energy=power;o.data.color=col;o.data.shape="DISK";o.data.size=size;aim(o,target)
# Broad stage and distant architecture sit behind the performance lane.
L=C["location"]; ground=M["stone"] if L in ("vesper","court","parliament","archive","broadcast") else M["brown"]
cube("ground",(0,0,-.35),(70,70,.7),ground)
if L in ("vesper","city","broadcast"):
 for i in range(15):
  x=-21+i*3; h=random.uniform(7,16); cube("distant tower",(x,17,h/2),(2.5,3,h),M["glass"] if i%3==0 else M["stone"])
  for z in range(2,int(h),3): cube("window",(x,15.45,z),(.35,.04,.55),M["lamp"])
if L in ("court","parliament","council","archive","broadcast"):
 for x in (-10,10):
  cube("civic wing",(x,9,4),(6,5,8),M["stone"])
  for z in (2,4,6):
   for xx in (-1.5,1.5): cube("deep window",(x+xx,6.43,z),(.8,.05,1.2),M["glass"])
 cube("rear facade",(0,11,4),(14,1,8),M["stone"])
if L in ("border","war","camp","marrow"):
 for i in range(12): cube("distant ridge",(-18+i*3.3,18,1.5),(4,3,3),M["coat"])
 for x in (-12,12): cube("ruined wall",(x,5,1.4),(4,1,2.8),M["stone"])
if L in ("camp","border"):
 for x in (-8,0,8):
  cube("aid tent",(x,8,1.4),(4,3,2.8),M["white"]);cube("tent roof",(x,8,2.9),(4.5,3.5,.3),M["coat"])
if L in ("registry","vesper","court","parliament","archive"):
 for i in range(5): cube("record cabinet",(-13+i*2.3,2,1.2),(1.7,.9,2.4),M["wood"])
if L in ("war","marrow"):
 for i in range(6): cube("rubble",(-15+i*6,-5,.25),(1.5,1.3,.5),M["stone"])
# Proper armature-driven voxel figures. Each limb has its own weighted rigid mesh.
def actor(name,x,y,skin,torso,legs):
 root=bpy.data.objects.new(name+" root",None);bpy.context.collection.objects.link(root);root.location=(x,y,0)
 ad=bpy.data.armatures.new(name+" rig");arm=bpy.data.objects.new(name+" RIG",ad);bpy.context.collection.objects.link(arm);arm.parent=root
 bpy.context.view_layer.objects.active=arm;arm.select_set(True);bpy.ops.object.mode_set(mode="EDIT")
 specs=[("root",(0,0,.1),(0,0,.9),None),("spine",(0,0,.85),(0,0,1.35),"root"),("head",(0,0,1.35),(0,0,1.85),"spine"),("arm.L",(-.32,0,1.28),(-.62,0,.68),"spine"),("arm.R",(.32,0,1.28),(.62,0,.68),"spine"),("leg.L",(-.16,0,.82),(-.18,0,.1),"root"),("leg.R",(.16,0,.82),(.18,0,.1),"root")]
 for n,h,t,p in specs:
  b=ad.edit_bones.new(n);b.head=h;b.tail=t
  if p:b.parent=ad.edit_bones[p]
 bpy.ops.object.mode_set(mode="OBJECT");arm.select_set(False)
 def block(n,loc,dim,ma,bone):
  o=cube(name+" "+n,(0,0,0),dim,ma);o.parent=root;o.location=loc
  g=o.vertex_groups.new(name=bone);g.add(list(range(len(o.data.vertices))),1,"REPLACE")
  mod=o.modifiers.new("rig deformation","ARMATURE");mod.object=arm
 block("torso",(0,0,1.1),(.66,.36,.78),torso,"spine");block("head",(0,0,1.66),(.55,.48,.55),skin,"head")
 block("hair",(0,0,1.96),(.58,.5,.12),M["cloth"],"head")
 block("arm L",(-.48,0,1.0),(.22,.32,.72),torso,"arm.L");block("arm R",(.48,0,1.0),(.22,.32,.72),torso,"arm.R")
 block("hand L",(-.48,0,.62),(.22,.3,.18),skin,"arm.L");block("hand R",(.48,0,.62),(.22,.3,.18),skin,"arm.R")
 block("leg L",(-.17,0,.42),(.26,.36,.82),legs,"leg.L");block("leg R",(.17,0,.42),(.26,.36,.82),legs,"leg.R")
 block("eye L",(-.12,-.247,1.7),(.055,.025,.055),M["white"],"head");block("eye R",(.12,-.247,1.7),(.055,.025,.055),M["white"],"head")
 return root,arm
hero,rig=actor("Kaylen Atlee",-2,-1,M["dark"],M["coat"],M["brown"]); cast=[(hero,rig)]
for i,s in enumerate(C.get("support",[])):
 r,a=actor(s,2+i*1.5,0,M["skin"] if i%2 else M["dark"],M["blue"] if i%2 else M["cloth"],M["coat"]);cast.append((r,a))
# Scene-defining props.
for p in C.get("props",[]):
 if p=="registry":cube("registry desk",(0,2,.7),(6,1.2,1.4),M["wood"])
 if p=="aircraft":cube("Flight 118 fuselage",(11,9,3),(9,2,2),M["white"])
 if p=="flag":cube("flag pole",(10,2,4),(.15,.15,8),M["wood"]);cube("brown flag",(11,2,6),(2,.12,1.2),M["brown"])
 if p=="armoured":cube("armoured vehicle",(11,-1,1),(4.5,2.5,1.8),M["coat"])
 if p=="papers":
  for i in range(12):cube("scattered evidence",(-5+i*.8,-3,.04),(.7,.8,.03),M["paper"])
 if p=="broadcast":cube("broadcast camera",(7,0,2),(1.5,.8,1.8),M["cloth"])
 if p=="water":cube("water tank",(10,6,2),(3,3,4),M["blue"])
 if p=="fire":
  for i in range(8):cube("embers",(-8+i*2,-4,.7),(.45,.45,1.4),M["fire"])
light("warm soft key",(-7,-10,14),2100,(1,.78,.58),9,(0,0,1))
light("cool fill",(8,-4,8),1200,(.48,.65,1),8,(0,0,1))
light("rim",(1,9,11),2200,(1,.52,.28),7,(0,0,1))
w=bpy.data.worlds.new("BROWN atmosphere");bpy.context.scene.world=w;w.use_nodes=True;w.node_tree.nodes["Background"].inputs[0].default_value=(.045,.06,.08,1);w.node_tree.nodes["Background"].inputs[1].default_value=.5
bpy.ops.object.camera_add(location=(0,-17,8));cam=bpy.context.object;cam.data.lens=42;bpy.context.scene.camera=cam
S=bpy.context.scene;S.render.fps=20;S.frame_start=START_FRAME;S.frame_end=END_FRAME
def animate(arm,style,a,b,phase):
 for f in range(a,b+1,20):
  t=(f-a)/20+phase;v=sin(t*2*pi/3)*(.62 if style in ("run","walk") else .13)
  for bn,rot in [("leg.L",(v,0,0)),("leg.R",(-v,0,0)),("arm.L",(-v*.8,0,0)),("arm.R",(v*.8,0,0)),("spine",(0,0,sin(t*.4)*.04)),("head",(0,0,sin(t*.2)*.07))]:
   pb=arm.pose.bones[bn];pb.rotation_mode="XYZ";pb.rotation_euler=rot;pb.keyframe_insert(data_path="rotation_euler",frame=f)
# Six 50-second shots: establish, medium, profile, low hero, geography, close.
for i,sh in enumerate(C["shots"]):
 a=1+i*1000;b=(i+1)*1000;mode=sh.get("camera","medium")
 loc,target={"wide":((0,-25,11),(0,2,1)),"low":((-7,-13,3.4),(0,0,1.1)),"profile":((13,-13,6),(0,0,1.1)),"overhead":((0,-10,19),(0,0,0)),"close":((-3,-10,4.5),(0,0,1.55))}.get(mode,((2,-17,7),(0,0,1.1)))
 cam.location=loc;aim(cam,target);cam.keyframe_insert(data_path="location",frame=a);cam.keyframe_insert(data_path="rotation_euler",frame=a)
 cam.location=(loc[0]+sh.get("dolly",.8),loc[1]+1,loc[2]+.2);aim(cam,target);cam.keyframe_insert(data_path="location",frame=b);cam.keyframe_insert(data_path="rotation_euler",frame=b)
 S.timeline_markers.new(sh["name"],frame=a)
 for j,(root,arm) in enumerate(cast):
  style=sh.get("action","walk") if j==0 else sh.get("support_action","observe")
  animate(arm,"brace" if style=="observe" else style,a,b,j*.7+i*.35)
  root.location.x=(-2+sh.get("hero_x",0)) if j==0 else 2+j*1.5;root.location.y=-1 if j==0 else 0
  root.keyframe_insert(data_path="location",frame=a);root.location.x+=sh.get("move_x",.6);root.keyframe_insert(data_path="location",frame=b)
# Fast deterministic raster rendering for the CPU-only GitHub runners.
# The scene is deliberately built from clear, material-coloured 3D geometry;
# Workbench preserves that palette and adds studio lighting, shadows and cavity.
S.render.engine = "BLENDER_WORKBENCH"
shade = S.display.shading
shade.light = "STUDIO"
shade.color_type = "MATERIAL"
shade.background_type = "WORLD"
shade.show_shadows = True
shade.show_cavity = True
shade.cavity_type = "WORLD"
shade.cavity_ridge_factor = 1.2
shade.cavity_valley_factor = 1.0
shade.show_specular_highlight = True
shade.studiolight_rotate_z = math.radians(18)
S.render.resolution_x=1280;S.render.resolution_y=720;S.render.resolution_percentage=100
S.render.image_settings.file_format="PNG";S.render.image_settings.color_mode="RGB"
S.render.filepath=os.path.abspath("render/frame_");S.view_settings.view_transform="AgX";S.view_settings.look="AgX - Medium High Contrast"

S["film"]="BROWN Book One";S["part"]=P;S["chapters"]=C["chapters"];S["camera_note"]="Unobstructed action lane, full character silhouettes, six cinematic angles."
print("BROWN_RENDER_BEGIN",P,C["title"],f"frames {START_FRAME}-{END_FRAME}",flush=True);bpy.ops.render.render(animation=True);print("BROWN_RENDER_COMPLETE",P,"PNG sequence",flush=True)
