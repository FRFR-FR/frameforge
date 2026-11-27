#!/usr/bin/env python3
"""Five original animated Blender cutaways. Conceptual explanations, not actual machine footage."""
import bpy, math, os, sys
from mathutils import Vector
args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
out=os.path.abspath(args[args.index("--output-dir")+1]) if "--output-dir" in args else os.path.abspath("output/3d_frames")
os.makedirs(out,exist_ok=True)
W,H,FPS,FRAMES=1280,720,24,120

def mat(n,c,metal=0.2,emit=None):
 m=bpy.data.materials.new(n); m.diffuse_color=(*c,1); m.use_nodes=True
 p=m.node_tree.nodes.get("Principled BSDF"); p.inputs["Base Color"].default_value=(*c,1); p.inputs["Metallic"].default_value=metal; p.inputs["Roughness"].default_value=.25
 if emit:
  p.inputs["Emission Color"].default_value=(*emit,1); p.inputs["Emission Strength"].default_value=2.8
 return m
STEEL=mat("machined steel",(.19,.28,.39),.8); DARK=mat("deep navy chamber",(.008,.02,.04),.5)
SILVER=mat("optical multilayer",(.65,.75,.86),.9); WAFER=mat("silicon",(.06,.23,.42),.8)
GOLD=mat("reticle carrier",(.5,.32,.09),.7); RED=mat("laser",(.9,.025,.04),.1,(1,.01,.02))
CYAN=mat("EUV path",(.02,.36,.9),.2,(.02,.28,1)); HOT=mat("plasma", (1,.2,.015),.1,(1,.1,.005)); WHITE=mat("ceramic",(.85,.9,.96),.1)
def cube(n,loc,dim,m,bevel=.05):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.name=n; o.dimensions=dim; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(m)
 if bevel: b=o.modifiers.new("edge bevel","BEVEL"); b.width=bevel; b.segments=3
 return o
def sphere(n,loc,r,m):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,radius=r,location=loc); o=bpy.context.object; o.name=n; o.data.materials.append(m); bpy.ops.object.shade_smooth(); return o
def cyl(n,loc,r,depth,m):
 bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=r,depth=depth,location=loc); o=bpy.context.object; o.name=n; o.data.materials.append(m); o.modifiers.new("edge bevel","BEVEL").width=.03; return o
def beam(n,a,b,r,m):
 a,b=Vector(a),Vector(b); v=b-a; o=cyl(n,(a+b)/2,r,v.length,m); o.rotation_euler=v.to_track_quat("Z","Y").to_euler(); return o
def animate(o,start,end):
 o.location=start; o.keyframe_insert(data_path="location",frame=1); o.location=end; o.keyframe_insert(data_path="location",frame=FRAMES)
def setup(folder,camloc=(8,-12,7),target=(0,0,0)):
 scene=bpy.context.scene; bpy.ops.object.camera_add(location=camloc); cam=bpy.context.object; cam.rotation_euler=(Vector(target)-cam.location).to_track_quat("-Z","Y").to_euler(); scene.camera=cam
 world=bpy.data.worlds.new("studio world"); scene.world=world; world.use_nodes=True; world.node_tree.nodes["Background"].inputs["Color"].default_value=(.006,.014,.028,1); world.node_tree.nodes["Background"].inputs["Strength"].default_value=.35
 for loc,power,size,col in [((2,-7,9),1700,8,(.7,.82,1)),((-6,2,5),1300,6,(.18,.4,1)),((5,5,4),900,5,(1,.28,.12))]:
  bpy.ops.object.light_add(type="AREA",location=loc); l=bpy.context.object; l.data.energy=power; l.data.shape="DISK"; l.data.size=size; l.data.color=col; l.rotation_euler=(Vector((0,0,0))-l.location).to_track_quat("-Z","Y").to_euler()
 available_engines={item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items}
 scene.render.engine="BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in available_engines else "BLENDER_EEVEE"
 scene.render.resolution_x=W; scene.render.resolution_y=H; scene.render.resolution_percentage=100
 scene.render.fps=FPS; scene.frame_start=1; scene.frame_end=FRAMES
 scene.render.image_settings.file_format="PNG"; scene.render.image_settings.color_mode="RGB"
 scene.render.filepath=os.path.join(folder,"frame_"); scene.view_settings.view_transform="AgX"
def clear():
 bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
def scene_tin(folder):
 clear(); cube("dark chamber",(0,0,-.8),(10,5,.3),DARK)
 for i in range(8):
  o=sphere("molten tin droplet",(-3.4+i*.55,0,.1),.15,HOT); animate(o,(-3.4+i*.55,0,.1),(-2.9+i*.55,0,.1))
 beam("focused laser beam",(-3,-2,2),(0,0,.2),.045,RED); p=sphere("plasma burst",(1,0,.25),.24,HOT)
 p.scale=(.4,.4,.4); p.keyframe_insert(data_path="scale",frame=1); p.scale=(2.0,1.5,1.5); p.keyframe_insert(data_path="scale",frame=55); p.scale=(.8,.8,.8); p.keyframe_insert(data_path="scale",frame=120)
 setup(folder,(6,-9,5),(0,0,0))
def scene_mirrors(folder):
 clear(); cube("vacuum base",(0,0,-.6),(11,5,.4),DARK)
 for y in [-1.7,1.7]: cube("open chamber rail",(0,y,.55),(9,.15,2.4),STEEL)
 specs=[((-2.6,0,.9),.42),( (0,0,1.35),-.5),((2.6,0,.9),.42)]
 for loc,ang in specs:
  m=cube("multilayer mirror",loc,(1.7,.17,1.1),SILVER); m.rotation_euler[1]=ang
 pts=[(-4,0,.1),(-2.6,0,1.15),(0,0,.85),(2.6,0,1.15),(4,0,.1)]
 for a,b in zip(pts,pts[1:]): beam("reflected EUV path",a,b,.035,CYAN)
 p=sphere("EUV pulse",pts[0],.14,CYAN); animate(p,pts[0],pts[-1]); cyl("wafer",(4.25,0,-.25),.9,.13,WAFER)
 setup(folder,(7,-11,6),(0,0,.5))
def scene_reticle(folder):
 clear(); cube("base",(0,0,-.65),(10,6,.3),DARK)
 cube("reflective reticle",(-1.8,0,1.8),(2.5,2,.12),GOLD)
 for i in range(-4,5): cube("mask pattern",(-1.8+i*.24,0,1.88),(.055,1.5,.02),DARK,.005)
 for i in range(8):
  beam("projected beam",(-2.8+i*.28,0,1.65),(.6+i*.15,0,.2),.012,CYAN)
 wafer=cyl("resist coated wafer",(1,0,-.02),1.6,.13,WAFER); animate(wafer,(1,0,-.02),(.75,0,-.02))
 for i in range(-4,5): cube("exposed resist pattern",(1+i*.24,0,.055),(.045,2.4,.02),WHITE,.003)
 setup(folder,(6,-10,6),(0,0,.55))
def scene_stage(folder):
 clear(); cyl("precision stage base",(0,0,-.1),2.1,.5,STEEL); cyl("magnetic ring",(0,0,.25),1.75,.13,GOLD)
 for a in range(0,360,45):
  r=math.radians(a); x,y=1.85*math.cos(r),1.85*math.sin(r)
  cyl("precision actuator",(x,y,.6),.11,.65,STEEL); beam("metrology beam",(x*1.1,y*1.1,1),(0,0,1.5),.015,CYAN)
 w=cyl("wafer on stage",(0,0,1.25),1.7,.12,WAFER); animate(w,(-.12,0,1.25),(.12,0,1.25))
 setup(folder,(7,-10,5.5),(0,0,.5))
def scene_layers(folder):
 clear(); cube("studio floor",(0,0,-.6),(9,7,.3),DARK)
 for i in range(6):
  z=.05+i*.28; disk=cyl("interconnected circuit layer",(0,0,z),1.8,.11,WAFER if i%2==0 else STEEL)
  for j in range(-3,4):
   o=cube("interconnect trace",(j*.42,0,z+.08),(.035,2.8,.02),CYAN,.005); o.rotation_euler[2]=i*.1
  animate(disk,(0,0,z+1),(0,0,z))
 setup(folder,(7,-11,6),(0,0,.6))
SCENES=[("scene_04_tin_plasma",scene_tin),("scene_05_mirror_optics",scene_mirrors),("scene_06_reticle_projection",scene_reticle),("scene_07_wafer_stage",scene_stage),("scene_08_layer_stack",scene_layers)]
for name,fn in SCENES:
 folder=os.path.join(out,name); os.makedirs(folder,exist_ok=True); fn(folder); bpy.ops.render.render(animation=True); print("RENDERED",name,flush=True)