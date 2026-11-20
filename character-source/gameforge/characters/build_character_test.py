#!/usr/bin/env python3
import bpy,sys,math,os
from mathutils import Vector
from pathlib import Path
NAMES=["Aster","Bront","Koro","Luma","Miri","Nyx","Orin","Pika","Sola","Vey"]
def arg():
 a=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
 import argparse;p=argparse.ArgumentParser();p.add_argument("--output-dir",default="output/gameforge_character_test");return p.parse_args(a)
def M(n,c,met=.2,rough=.4):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;b=m.node_tree.nodes["Principled BSDF"];b.inputs["Base Color"].default_value=(*c,1);b.inputs["Metallic"].default_value=met;b.inputs["Roughness"].default_value=rough;return m
def box(n,p,s,m,col):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.name=n;o.dimensions=s;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(m)
 q=o.modifiers.new("EdgeBevel","BEVEL");q.width=.035;q.segments=2
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o);return o
def sph(n,p,s,m,col):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,location=p);o=bpy.context.object;o.name=n;o.scale=s;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(m)
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o);return o
def bone(r,n,parent,h,t):
 b=r.data.edit_bones.new(n);b.head=h;b.tail=t
 if parent:b.parent=r.data.edit_bones[parent]
def rig(name):
 bpy.ops.object.armature_add(enter_editmode=True);r=bpy.context.object;r.name=name+"_Rig";r.data.name=name+"_Skeleton";[r.data.edit_bones.remove(b) for b in list(r.data.edit_bones)]
 bone(r,"root",None,(0,0,0),(0,0,.2));bone(r,"pelvis","root",(0,0,.9),(0,0,1.1));bone(r,"spine","pelvis",(0,0,1.1),(0,0,1.5));bone(r,"neck","spine",(0,0,1.5),(0,0,1.7));bone(r,"head","neck",(0,0,1.7),(0,0,1.95))
 for s in (-1,1):
  q="L" if s<0 else "R";bone(r,"upper_arm."+q,"spine",(s*.25,0,1.45),(s*.55,0,1.3));bone(r,"forearm."+q,"upper_arm."+q,(s*.55,0,1.3),(s*.8,0,1.1));bone(r,"hand."+q,"forearm."+q,(s*.8,0,1.1),(s*.92,0,1.08));bone(r,"thigh."+q,"pelvis",(s*.13,0,.9),(s*.18,0,.5));bone(r,"shin."+q,"thigh."+q,(s*.18,0,.5),(s*.19,0,.1));bone(r,"foot."+q,"shin."+q,(s*.19,0,.1),(s*.19,-.22,.05))
 bpy.ops.object.mode_set(mode="OBJECT");r["character_id"]=name;return r
def make_action(rig,name,keys):
 action=bpy.data.actions.new(rig.name.replace("_Rig","")+"_"+name)
 rig.animation_data_create()
 rig.animation_data.action=action
 for frame,pose in keys:
  for pb in rig.pose.bones:
   pb.rotation_mode="XYZ"
   pb.rotation_euler=pose.get(pb.name,(0.0,0.0,0.0))
   pb.keyframe_insert(data_path="rotation_euler",frame=frame,group=pb.name)
 for fc in getattr(action,"fcurves",[]):
  for point in fc.keyframe_points: point.interpolation="BEZIER"
 return action

def locomotion_actions(rig):
 neutral={}
 make_action(rig,"Idle",[
  (1,{"spine":(0.0,0.0,0.0)}),(12,{"spine":(0.0,0.018,0.0),"head":(0.0,0.0,0.025)}),
  (24,{"spine":(0.0,0.0,0.0)}),(36,{"spine":(0.0,-0.018,0.0),"head":(0.0,0.0,-0.025)}),(48,neutral)])
 make_action(rig,"Walk",[
  (1,neutral),(7,{"thigh.L":(0.42,0,0),"shin.L":(-0.20,0,0),"thigh.R":(-0.42,0,0),"shin.R":(0.20,0,0),"upper_arm.L":(-0.26,0,0),"upper_arm.R":(0.26,0,0),"spine":(0.04,0,0)}),
  (13,neutral),(19,{"thigh.L":(-0.42,0,0),"shin.L":(0.20,0,0),"thigh.R":(0.42,0,0),"shin.R":(-0.20,0,0),"upper_arm.L":(0.26,0,0),"upper_arm.R":(-0.26,0,0),"spine":(0.04,0,0)}),(25,neutral)])
 make_action(rig,"Sprint",[
  (1,{"spine":(0.20,0,0),"upper_arm.L":(-0.62,0,-0.15),"upper_arm.R":(-0.62,0,0.15),"forearm.L":(-0.72,0,0),"forearm.R":(-0.72,0,0),"thigh.L":(0.72,0,0),"thigh.R":(-0.72,0,0),"shin.L":(-0.48,0,0),"shin.R":(0.48,0,0)}),
  (7,{"spine":(0.20,0,0),"upper_arm.L":(0.42,0,-0.15),"upper_arm.R":(0.42,0,0.15),"forearm.L":(-0.72,0,0),"forearm.R":(-0.72,0,0),"thigh.L":(-0.72,0,0),"thigh.R":(0.72,0,0),"shin.L":(0.48,0,0),"shin.R":(-0.48,0,0)}),
  (13,{"spine":(0.20,0,0),"upper_arm.L":(-0.62,0,-0.15),"upper_arm.R":(-0.62,0,0.15),"forearm.L":(-0.72,0,0),"forearm.R":(-0.72,0,0),"thigh.L":(0.72,0,0),"thigh.R":(-0.72,0,0),"shin.L":(-0.48,0,0),"shin.R":(0.48,0,0)}),
  (19,{"spine":(0.20,0,0),"upper_arm.L":(0.42,0,-0.15),"upper_arm.R":(0.42,0,0.15),"forearm.L":(-0.72,0,0),"forearm.R":(-0.72,0,0),"thigh.L":(-0.72,0,0),"thigh.R":(0.72,0,0),"shin.L":(0.48,0,0),"shin.R":(-0.48,0,0)}),
  (25,{"spine":(0.20,0,0),"upper_arm.L":(-0.62,0,-0.15),"upper_arm.R":(-0.62,0,0.15),"forearm.L":(-0.72,0,0),"forearm.R":(-0.72,0,0),"thigh.L":(0.72,0,0),"thigh.R":(-0.72,0,0),"shin.L":(-0.48,0,0),"shin.R":(0.48,0,0)} )])
 make_action(rig,"Crouch",[
  (1,{"spine":(0.23,0,0),"pelvis":(0.10,0,0),"thigh.L":(0.62,0,0),"thigh.R":(0.62,0,0),"shin.L":(-1.10,0,0),"shin.R":(-1.10,0,0),"upper_arm.L":(-0.12,0,0),"upper_arm.R":(-0.12,0,0)}),
  (24,{"spine":(0.23,0,0),"pelvis":(0.10,0,0),"thigh.L":(0.62,0,0),"thigh.R":(0.62,0,0),"shin.L":(-1.10,0,0),"shin.R":(-1.10,0,0),"upper_arm.L":(-0.12,0,0),"upper_arm.R":(-0.12,0,0)})])
 make_action(rig,"Jump",[
  (1,neutral),(5,{"spine":(-0.12,0,0),"upper_arm.L":(-0.7,0,0),"upper_arm.R":(-0.7,0,0),"thigh.L":(0.35,0,0),"thigh.R":(0.35,0,0),"shin.L":(-0.65,0,0),"shin.R":(-0.65,0,0)}),
  (13,{"spine":(-0.12,0,0),"upper_arm.L":(-0.7,0,0),"upper_arm.R":(-0.7,0,0),"thigh.L":(0.35,0,0),"thigh.R":(0.35,0,0),"shin.L":(-0.65,0,0),"shin.R":(-0.65,0,0)}),(22,neutral)])
 make_action(rig,"Roll",[
  (1,{"spine":(0.55,0,0),"head":(-0.18,0,0),"upper_arm.L":(0.30,0,-0.5),"upper_arm.R":(0.30,0,0.5),"thigh.L":(0.85,0,0),"thigh.R":(0.85,0,0),"shin.L":(-1.0,0,0),"shin.R":(-1.0,0,0)}),
  (8,{"spine":(0.90,0,0),"head":(-0.30,0,0),"upper_arm.L":(0.45,0,-0.7),"upper_arm.R":(0.45,0,0.7),"thigh.L":(1.0,0,0),"thigh.R":(1.0,0,0),"shin.L":(-1.05,0,0),"shin.R":(-1.05,0,0)}),
  (16,{"spine":(0.45,0,0),"head":(-0.12,0,0),"upper_arm.L":(0.20,0,-0.35),"upper_arm.R":(0.20,0,0.35),"thigh.L":(0.55,0,0),"thigh.R":(0.55,0,0),"shin.L":(-0.6,0,0),"shin.R":(-0.6,0,0)}),(24,neutral)])
 make_action(rig,"Fire",[
  (1,{"upper_arm.L":(-0.25,0,0.2),"upper_arm.R":(-0.35,0,-0.2),"forearm.L":(-0.15,0,0),"forearm.R":(-0.55,0,0),"spine":(0.06,0,0)}),
  (5,{"upper_arm.L":(-0.23,0,0.2),"upper_arm.R":(-0.28,0,-0.2),"forearm.L":(-0.13,0,0),"forearm.R":(-0.50,0,0),"spine":(0.04,0,0)}),(10,neutral)])
 make_action(rig,"Reload",[
  (1,{"upper_arm.L":(-0.20,0,0.45),"forearm.L":(-0.8,0,0),"upper_arm.R":(-0.25,0,-0.25),"forearm.R":(-0.75,0,0)}),
  (9,{"upper_arm.L":(-0.35,0,0.42),"forearm.L":(-1.0,0,0),"upper_arm.R":(-0.18,0,-0.18),"forearm.R":(-0.95,0,0)}),(18,neutral)])
 make_action(rig,"Emote_Wave",[
  (1,{"upper_arm.R":(0.10,0,-0.75),"forearm.R":(0,0,-0.85)}),(10,{"upper_arm.R":(0.1,0,-1.35),"forearm.R":(0,0,-1.0),"hand.R":(0,0,0.35)}),
  (18,{"upper_arm.R":(0.1,0,-1.35),"forearm.R":(0,0,-1.0),"hand.R":(0,0,-0.35)}),(26,neutral)])
 make_action(rig,"Emote_Guard",[
  (1,{"spine":(0.1,0,0),"upper_arm.L":(0,0,0.85),"forearm.L":(0,0,-0.75),"upper_arm.R":(0,0,-0.85),"forearm.R":(0,0,0.75)}),(18,neutral)])
 make_action(rig,"Emote_Victory",[
  (1,{"upper_arm.L":(0,0,1.55),"forearm.L":(0,0,-0.25),"upper_arm.R":(0,0,-1.55),"forearm.R":(0,0,0.25)}),
  (18,{"spine":(-0.08,0,0),"upper_arm.L":(0,0,1.75),"forearm.L":(0,0,-0.38),"upper_arm.R":(0,0,-1.75),"forearm.R":(0,0,0.38)}),(36,neutral)])

def main():
 a=arg();out=Path(a.output_dir).resolve();(out/"characters").mkdir(parents=True,exist_ok=True);(out/"previews").mkdir(parents=True,exist_ok=True)
 bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
 for i,name in enumerate(NAMES):
  col=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(col);off=(i%5*2.7-5.4,i//5*3,0)
  suit=M(name+" Suit",(.025+.012*i,.045,.065+.008*i),.55,.3);arm=M(name+" Armor",(.16,.2,.24),.8,.23);acc=M(name+" Accent",(.08+.06*(i%3),.35+.04*(i%4),.55),.65,.24);skin=M(name+" Skin",(.36,.20,.13),.05,.5);glass=M(name+" Visor",(.02,.2,.25),.3,.15)
  meshes=[box("Torso",(off[0],off[1],1.25),(.62,.34,.62),suit,col),box("ChestPlate",(off[0],off[1]-.19,1.38),(.48,.05,.3),arm,col),box("Core",(off[0],off[1]-.22,1.38),(.14,.025,.1),acc,col),sph("Head",(off[0],off[1],1.82),(.22,.19,.25),skin,col),sph("Visor",(off[0],off[1]-.17,1.84),(.17,.03,.09),glass,col)]
  for s in (-1,1):
   q="L" if s<0 else "R";meshes += [box("Shoulder_"+q,(off[0]+s*.37,off[1],1.42),(.2,.38,.2),acc,col),box("Arm_"+q,(off[0]+s*.58,off[1],1.2),(.18,.2,.42),suit,col),box("Forearm_"+q,(off[0]+s*.7,off[1],1.0),(.17,.22,.34),arm,col),box("Thigh_"+q,(off[0]+s*.17,off[1],.68),(.2,.24,.45),suit,col),box("Shin_"+q,(off[0]+s*.19,off[1],.3),(.18,.22,.4),arm,col),box("Boot_"+q,(off[0]+s*.19,off[1]-.12,.07),(.22,.4,.16),suit,col)]
  r=rig(name);r.location=off
  for o in meshes:o.select_set(True)
  r.select_set(True);bpy.context.view_layer.objects.active=r;bpy.ops.object.parent_set(type="ARMATURE_AUTO");bpy.ops.object.select_all(action="DESELECT")
  locomotion_actions(r)
  r.animation_data.action=next((a for a in bpy.data.actions if a.name==name+"_Idle"),None)
  r.select_set(True)
  for o in meshes:o.select_set(True)
  bpy.context.view_layer.objects.active=r;bpy.ops.export_scene.gltf(filepath=str(out/"characters"/(name+".glb")),export_format="GLB",use_selection=True,export_animations=True,export_skins=True,export_materials="EXPORT",export_animation_mode="ACTIONS",export_force_sampling=True,export_cameras=False,export_lights=False);bpy.ops.object.select_all(action="DESELECT")
 bpy.ops.wm.save_as_mainfile(filepath=str(out/"GAMEFORGE_LOOMGLASS_10_Character_Lab.blend"))
 if os.environ.get("GAMEFORGE_SKIP_PREVIEWS") == "1":
  return
 scene=bpy.context.scene;scene.render.engine="BLENDER_EEVEE";scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100;scene.render.filepath=str(out/"previews/CHARACTERS_720p.png");bpy.ops.object.camera_add(location=(0,-18,7));cam=bpy.context.object;cam.data.type="ORTHO";cam.data.ortho_scale=15;cam.rotation_euler=(Vector((0,1.5,1.0))-cam.location).to_track_quat("-Z","Y").to_euler();scene.camera=cam;bpy.ops.object.light_add(type="AREA",location=(0,-8,10));bpy.context.object.data.energy=2200;bpy.context.object.data.size=10;bpy.ops.object.select_all(action="SELECT");bpy.ops.render.render(write_still=True)
 import shutil
 for n in NAMES:shutil.copy2(out/"previews/CHARACTERS_720p.png",out/"previews"/(n+"_720p.png"))
if __name__=="__main__":main()
