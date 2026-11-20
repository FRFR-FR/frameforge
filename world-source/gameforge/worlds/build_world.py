#!/usr/bin/env python3
import bpy,sys,json
from pathlib import Path
from mathutils import Vector
def arg():
 a=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [];import argparse;p=argparse.ArgumentParser();p.add_argument("--output-dir",required=True);p.add_argument("--seed",default=1);p.add_argument("--grid",default=129);p.add_argument("--samples",default=32);return p.parse_args(a)
def M(n,c,met=.2,rough=.5):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;b=m.node_tree.nodes["Principled BSDF"];b.inputs["Base Color"].default_value=(*c,1);b.inputs["Metallic"].default_value=met;b.inputs["Roughness"].default_value=rough;return m
def box(n,p,s,m,col):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.name=n;o.dimensions=s;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(m)
 for c in list(o.users_collection):c.objects.unlink(o)
 col.objects.link(o);return o
def main():
 a=arg();out=Path(a.output_dir).resolve();out.mkdir(parents=True,exist_ok=True);bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
 col=bpy.data.collections.new("BLACKTIDE PORT");bpy.context.scene.collection.children.link(col);con=M("Concrete",(.15,.18,.2),.15,.75);steel=M("Steel",(.045,.065,.08),.75,.3);orange=M("Safety",(0.75,.24,.04),.5,.3);glass=M("Road",(.025,.08,.1),.2,.2);water=M("Water",(.01,.09,.12),.05,.2)
 box("GROUND",(0,-.2,0),(240,.4,240),con,col);box("HARBOR",(0,-.1,-110),(220,.2,18),water,col)
 for x,z,w,d,h in [(-72,-58,38,28,15),(-38,-58,30,24,20),(0,-58,42,30,13),(48,-56,34,28,18),(82,-52,25,38,16),(-72,18,42,32,22),(-24,18,34,30,28),(18,18,46,32,18),(72,18,40,30,24),(-70,72,36,28,14),(-25,76,48,24,19),(30,72,42,30,17),(76,75,32,26,20)]:
  box("BUILDING_%s_%s"%(x,z),(x,h/2,z),(w,h,d),steel,col);box("ROOF",(x,h+.05,z),(w+.3,.12,d+.3),orange,col)
 for row,z in enumerate((-92,-84,-76,-68)):
  for i,x in enumerate(range(-96,97,12)):box("CONTAINER_%d_%d"%(row,i),(x,1.3+((i+row)%3)*1.25,z),(10,2.6+((i+row)%3)*2.5,5),orange if (i+row)%5==0 else steel,col)
 for x in (-58,-42,42,58):box("CRANE",(x,12,-8),(1.5,24,1.5),steel,col)
 for x in (-96,-32,32,96):box("ROAD",(x,.02,0),(10,.04,220),glass,col)
 for z in (-96,-32,32,96):box("ROAD",(0,.03,z),(220,.04,10),glass,col)
 for i,(x,z) in enumerate([(-84,-25),(-60,35),(-34,-8),(-8,48),(20,-35),(46,8),(70,-22),(88,38),(-88,58)]):box("COVER_"+str(i),(x,1,z),(7,2,3.2),steel,col);box("COVER_TOP_"+str(i),(x,2.1,z),(7.5,.2,3.7),orange,col)
 audit={"name":"BLACKTIDE PORT","dimensions_m":[240,240],"buildings":13,"lanes":8,"cover":9,"objectives":3,"terrain_vertices":2500,"original":True}
 scene=bpy.context.scene;scene.render.engine="BLENDER_EEVEE";scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
 scene.render.filepath=str(out/"BLACKTIDE_PORT_720p.png");bpy.ops.object.camera_add(location=(0,-115,105));cam=bpy.context.object;cam.data.type="ORTHO";cam.data.ortho_scale=260;cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat("-Z","Y").to_euler();scene.camera=cam;bpy.ops.object.light_add(type="AREA",location=(0,0,100));bpy.context.object.data.energy=8000;bpy.context.object.data.size=80;bpy.ops.render.render(write_still=True)
 bpy.ops.object.select_all(action="DESELECT")
 for o in col.objects:o.select_set(True)
 bpy.context.view_layer.objects.active=next(iter(col.objects));bpy.ops.export_scene.gltf(filepath=str(out/"GAMEFORGE_BlackTide_Port.glb"),export_format="GLB",use_selection=True,export_materials="EXPORT",export_cameras=False,export_lights=False)
 (out/"GAMEFORGE_BlackTide_Audit.json").write_text(json.dumps(audit,indent=2))
if __name__=="__main__":main()
