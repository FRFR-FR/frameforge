#!/usr/bin/env python3
"""GAMEFORGE Loomglass: ten original, rigged Blender characters and 720p previews."""
import argparse, json, math, os, sys, time, zipfile
from pathlib import Path
import bpy
from mathutils import Vector

STYLE="LOOMGLASS"; W,H=1280,720; FPS=30; END=72
CAST=[
("Aster","Wayfinder",(0.25,.62,.61),(.025,.10,.16),(.98,.56,.22),(.15,.92,.82),"halo"),
("Bront","Oathkeeper",(.62,.34,.26),(.13,.06,.07),(.91,.28,.22),(1,.54,.28),"horns"),
("Nyx","Verdantist",(.32,.57,.37),(.04,.14,.11),(.62,.82,.36),(.35,1,.57),"leaves"),
("Pika","Spark-runner",(.83,.49,.27),(.19,.09,.035),(1,.72,.22),(1,.85,.35),"comet"),
("Orin","Memory-keeper",(.40,.43,.72),(.08,.07,.19),(.57,.48,.96),(.62,.72,1),"archive"),
("Sola","Cloud courier",(.57,.73,.84),(.07,.16,.25),(.43,.78,.94),(.67,.92,1),"wings"),
("Vey","Forge-singer",(.70,.39,.21),(.13,.075,.035),(.92,.38,.13),(1,.40,.13),"forge"),
("Luma","Tidecaller",(.64,.47,.75),(.13,.08,.21),(.36,.78,.83),(.45,.94,1),"tide"),
("Koro","Dusk ranger",(.38,.31,.48),(.055,.045,.10),(.62,.35,.81),(.83,.48,1),"crescent"),
("Miri","Seed-tender",(.86,.55,.40),(.22,.10,.085),(.96,.58,.40),(1,.70,.48),"petals")]

def args():
    p=argparse.ArgumentParser(); p.add_argument("--output-dir",default="output/gameforge_character_test"); p.add_argument("--samples",type=int,default=48)
    parsed,_unknown=p.parse_known_args(sys.argv[1:]); return parsed
def mat(n,c,rough=.42,metal=0,emit=None):
    m=bpy.data.materials.new(n); m.diffuse_color=(*c,1); m.use_nodes=True; b=m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value=(*c,1); b.inputs["Roughness"].default_value=rough; b.inputs["Metallic"].default_value=metal
    if b.inputs.get("Coat Weight"): b.inputs["Coat Weight"].default_value=.28
    if emit:
        e=b.inputs.get("Emission Color") or b.inputs.get("Emission")
        if e: e.default_value=(*emit,1)
        if b.inputs.get("Emission Strength"): b.inputs["Emission Strength"].default_value=1.8
    return m

def coll(n):
    c=bpy.data.collections.new(n); bpy.context.scene.collection.children.link(c); return c

def finish(o,n,bone,m,c,bevel=0):
    o.name=n; o.data.materials.append(m)
    if bevel:
        mod=o.modifiers.new("Soft folded edge","BEVEL"); mod.width=bevel; mod.segments=3; bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=mod.name)
    o.vertex_groups.new(name=bone).add(list(range(len(o.data.vertices))),1,"REPLACE")
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    for p in getattr(o.data,"polygons",[]): p.use_smooth=True
    return o

def shape(parts,c,n,bone,m,kind,loc,scale,rot=(0,0,0)):
    if kind=="sphere": bpy.ops.mesh.primitive_uv_sphere_add(segments=28,ring_count=18,location=loc)
    elif kind=="cube": bpy.ops.mesh.primitive_cube_add(size=1,location=loc,rotation=rot)
    elif kind=="cone": bpy.ops.mesh.primitive_cone_add(vertices=28,radius1=scale[0],radius2=0,depth=scale[2],location=loc,rotation=rot); scale=(1,1,1)
    elif kind=="cylinder": bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=scale[0],depth=scale[2],location=loc,rotation=rot); scale=(1,1,1)
    elif kind=="torus": bpy.ops.mesh.primitive_torus_add(major_radius=scale[0],minor_radius=scale[1],major_segments=40,minor_segments=10,location=loc,rotation=rot); scale=(1,1,1)
    o=bpy.context.object
    if kind in ("sphere","cube"): o.scale=scale
    finish(o,n,bone,m,c,.08 if kind=="cube" else 0)
    for old in list(o.users_collection): old.objects.unlink(o)
    c.objects.link(o); parts.append(o); return o

def panel(parts,c,n,bone,m,verts):
    bpy.ops.object.select_all(action="DESELECT")
    me=bpy.data.meshes.new(n); me.from_pydata(verts,[],[(0,1,2,3)]); me.materials.append(m); me.update()
    o=bpy.data.objects.new(n,me); c.objects.link(o); o.vertex_groups.new(name=bone).add(list(range(len(me.vertices))),1,"REPLACE")
    s=o.modifiers.new("Fold thickness","SOLIDIFY"); s.thickness=.07; b=o.modifiers.new("Chamfer","BEVEL"); b.width=.03; b.segments=3
    bpy.context.view_layer.objects.active=o; o.select_set(True); bpy.ops.object.modifier_apply(modifier=s.name); bpy.ops.object.modifier_apply(modifier=b.name)
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True); parts.append(o); return o

def rod(parts,c,n,bone,m,a,b,r=.02):
    a,b=Vector(a),Vector(b); d=b-a; bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=r,depth=d.length,location=(a+b)/2)
    o=bpy.context.object; o.rotation_mode="QUATERNION"; o.rotation_quaternion=d.to_track_quat("Z","Y"); finish(o,n,bone,m,c)
    for old in list(o.users_collection): old.objects.unlink(o)
    c.objects.link(o); parts.append(o)

def rig(n,c):
    data=bpy.data.armatures.new(n+" skeleton"); r=bpy.data.objects.new(n+"_Rig",data); c.objects.link(r)
    bpy.ops.object.select_all(action="DESELECT"); bpy.context.view_layer.objects.active=r; r.select_set(True); bpy.ops.object.mode_set(mode="EDIT"); eb={}
    def add(k,h,t,parent=None,connect=False):
        b=data.edit_bones.new(k); b.head=h; b.tail=t
        if parent: b.parent=eb[parent]; b.use_connect=connect
        eb[k]=b
    add("root",(0,0,.05),(0,0,.45)); add("pelvis",(0,0,.9),(0,0,1.28),"root")
    add("spine",(0,0,1.28),(0,0,2.12),"pelvis",True); add("neck",(0,0,2.12),(0,0,2.46),"spine",True); add("head",(0,0,2.46),(0,0,3.12),"neck",True)
    for side,s in (("L",-1),("R",1)):
        add("upper_arm."+side,(s*.4,0,2.08),(s*.55,0,1.62),"spine"); add("forearm."+side,(s*.55,0,1.62),(s*.62,0,1.17),"upper_arm."+side,True); add("hand."+side,(s*.62,0,1.17),(s*.65,-.02,.98),"forearm."+side,True)
        add("thigh."+side,(s*.23,0,1.1),(s*.25,0,.64),"pelvis"); add("shin."+side,(s*.25,0,.64),(s*.25,0,.2),"thigh."+side,True); add("foot."+side,(s*.25,0,.2),(s*.25,-.28,.12),"shin."+side,True)
    bpy.ops.object.mode_set(mode="OBJECT"); r.select_set(False); return r

def build(spec,i):
    name,role,skin,cloth,accent,glow,signature=spec; c=coll("CHARACTER • %02d • %s"%(i,name)); parts=[]
    sk=mat(name+" ceramic",skin,.36,.08); cl=mat(name+" textile",cloth,.67,.02); ac=mat(name+" folded enamel",accent,.32,.25); gl=mat(name+" luminous seam",glow,.23,.12,glow); me=mat(name+" satin metal",tuple(min(1,x*1.15) for x in accent),.25,.72); dark=mat(name+" ink",tuple(x*.2 for x in cloth),.42,.1); white=mat(name+" ivory",(.9,.92,.88),.2)
    r=rig(name,c); P=lambda n,b,m,k,l,s,rot=(0,0,0):shape(parts,c,name+" "+n,b,m,k,l,s,rot)
    P("pelvis","pelvis",cl,"sphere",(0,0,1.12),(.43,.31,.39)); P("chest","spine",sk,"sphere",(0,0,1.82),(.52,.34,.68)); P("mantle core","spine",cl,"sphere",(0,.02,1.91),(.58,.35,.55)); P("folded chest plate","spine",ac,"cube",(0,-.34,1.92),(.7,.11,.48))
    P("throat ring","spine",me,"torus",(0,0,2.25),(.38,.055,1),(math.pi/2,0,0)); P("neck","neck",sk,"sphere",(0,0,2.35),(.19,.2,.28)); P("head","head",sk,"sphere",(0,0,2.76),(.47,.37,.56))
    for side,x in (("L",-.19),("R",.19)):
        P("socket "+side,"head",dark,"sphere",(x,-.343,2.77),(.145,.095,.175)); P("eye "+side,"head",white,"sphere",(x,-.408,2.78),(.108,.075,.132)); P("iris "+side,"head",ac,"sphere",(x,-.471,2.775),(.059,.035,.078)); P("pupil "+side,"head",dark,"sphere",(x,-.50,2.775),(.027,.02,.052)); P("brow "+side,"head",dark,"cube",(x,-.42,2.98),(.21,.06,.05))
    P("nose","head",sk,"sphere",(0,-.418,2.60),(.075,.075,.105)); P("mouth","head",dark,"cube",(0,-.424,2.455),(.19,.025,.035))
    for side,s in (("L",-1),("R",1)):
        ub,fb,hb="upper_arm."+side,"forearm."+side,"hand."+side; tb,sb,ft="thigh."+side,"shin."+side,"foot."+side
        P("shoulder "+side,ub,ac,"sphere",(s*.49,0,2.07),(.3,.34,.31)); P("upper arm "+side,ub,sk,"sphere",(s*.55,0,1.83),(.2,.23,.39)); P("forearm "+side,fb,cl,"sphere",(s*.61,0,1.39),(.18,.2,.34)); P("cuff "+side,fb,me,"cube",(s*.62,-.02,1.55),(.34,.31,.15)); P("glove "+side,hb,ac,"sphere",(s*.65,-.02,1.08),(.17,.18,.17))
        P("thigh "+side,tb,cl,"sphere",(s*.24,0,.8),(.23,.25,.39)); P("shin "+side,sb,sk,"sphere",(s*.25,-.01,.4),(.17,.19,.31)); P("boot "+side,ft,me,"cube",(s*.25,-.14,.13),(.33,.52,.22)); rod(parts,c,name+" arm seam "+side,fb,gl,(s*.61,-.2,1.28),(s*.61,-.2,1.53)); rod(parts,c,name+" shin seam "+side,sb,gl,(s*.25,-.2,.3),(s*.25,-.2,.54))
    P("belt","pelvis",me,"cube",(0,-.025,1.28),(.94,.46,.15)); P("belt jewel","pelvis",gl,"sphere",(0,-.27,1.28),(.13,.055,.13)); rod(parts,c,name+" sternum seam","spine",gl,(0,-.45,1.6),(0,-.45,2.2),.018)
    # Ten different silhouette signatures; every element is weighted to the appropriate bone.
    if signature=="halo":
        P("orbit halo","head",me,"torus",(0,.22,3.22),(.52,.055,1),(math.pi/2,0,0)); P("swept crest L","head",ac,"cone",(-.43,.1,3.26),(.19,1,.62),(0,-.55,-.35)); P("swept crest R","head",gl,"cone",(.43,.1,3.2),(.16,1,.48),(0,.65,.45))
    elif signature=="horns":
        P("horn L","head",me,"cone",(-.4,.04,3.23),(.2,1,.75),(0,-.45,-.2)); P("horn R","head",ac,"cone",(.4,.04,3.22),(.19,1,.7),(0,-.4,.25)); P("shield gorget","spine",me,"cube",(0,-.28,2.1),(.92,.18,.4)); P("furnace heart","spine",gl,"sphere",(0,-.43,1.83),(.16,.05,.18))
    elif signature=="leaves":
        for j,x in enumerate((-.42,0,.42)): P("leaf crown %d"%j,"head",gl if j==1 else ac,"cone",(x,.08,3.2),(.22,1,.72),(0,(j-1)*.55,0))
        panel(parts,c,name+" leaf mantle L","spine",ac,[(-.37,.24,2.18),(-.92,.37,1.08),(-.46,.32,1.36),(-.13,.22,1.9)]); panel(parts,c,name+" leaf mantle R","spine",gl,[(.37,.24,2.18),(.92,.37,1.08),(.46,.32,1.36),(.13,.22,1.9)])
    elif signature=="comet":
        for j in range(4): P("comet plume %d"%j,"head",ac if j%2==0 else gl,"cone",(-.25+j*.17,.12,3.38),(.12,1,.62),(0,-.35+j*.13,0))
        P("runner sash","spine",ac,"cube",(0,-.3,1.58),(.8,.08,.15),(0,0,-.2))
    elif signature=="archive":
        P("archive aureole","head",gl,"torus",(0,.32,2.9),(.72,.045,1),(math.pi/2,0,0)); P("visor","head",me,"cube",(0,-.35,3.02),(.84,.12,.13)); P("book clasp","spine",ac,"cube",(0,-.42,1.81),(.42,.12,.5))
    elif signature=="wings":
        for side,s in (("L",-1),("R",1)):
            panel(parts,c,name+" sky wing "+side,"spine",ac,[(s*.35,.2,2.26),(s*1.1,.5,2.72),(s*1.38,.55,1.48),(s*.52,.28,1.26)])
            P("feather "+side,"spine",gl,"cone",(s*.94,.34,1.85),(.12,1,.58),(0,s*.45,0))
    elif signature=="forge":
        P("anvil crest","head",ac,"cone",(0,.08,3.25),(.28,1,.58)); P("forge pauldron","upper_arm.L",me,"cube",(-.66,.02,2.06),(.55,.62,.48)); P("vent orb","upper_arm.L",gl,"sphere",(-.66,-.31,2.1),(.15,.08,.15)); P("hammer","hand.R",ac,"cube",(.86,-.03,1.17),(.42,.23,.3)); rod(parts,c,name+" hammer grip","hand.R",me,(.86,-.04,.7),(.86,-.04,1.1),.06)
    elif signature=="tide":
        P("tidal circlet","head",gl,"torus",(0,.18,3.17),(.55,.06,1),(math.pi/2,0,0))
        for j,x in enumerate((-.45,0,.45)): P("fin %d"%j,"head",ac if j!=1 else me,"cone",(x,.08,3.35),(.16,1,.6),(0,(j-1)*.42,0))
        panel(parts,c,name+" fin mantle L","spine",ac,[(-.36,.22,2.1),(-.87,.5,1.58),(-.64,.43,.86),(-.18,.25,1.3)])
        panel(parts,c,name+" fin mantle R","spine",gl,[(.36,.22,2.1),(.87,.5,1.58),(.64,.43,.86),(.18,.25,1.3)])
    elif signature=="crescent":
        P("crescent ring","head",me,"torus",(0,.28,3.0),(.64,.1,1),(math.pi/2,0,0)); P("shadow hood","head",dark,"cube",(0,.15,2.94),(.94,.53,.52)); P("hood tip","head",ac,"cone",(.34,.06,3.34),(.15,1,.48)); P("ranger mantle","spine",me,"cube",(0,.25,1.7),(.95,.26,.92))
    elif signature=="petals":
        for j in range(7):
            a=j*math.tau/7; P("petal %d"%j,"head",ac if j%2 else gl,"sphere",(math.sin(a)*.48,.16,3.1+math.cos(a)*.3),(.18,.13,.36))
        P("seed halo","head",me,"torus",(0,.18,2.95),(.49,.04,1),(math.pi/2,0,0))
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]; bpy.ops.object.join(); body=bpy.context.object; body.name=name+"_UnifiedSkinnedMesh"; body.data.name=name+"_LoomglassGeometry"; body.parent=r
    for old in list(body.users_collection): old.objects.unlink(body)
    c.objects.link(body)
    mod=body.modifiers.new("Armature deformation","ARMATURE"); mod.object=r
    body["character_id"]="%02d_%s"%(i,name.upper()); body["style"]=STYLE; body["single_unified_mesh"]=True; r["character_id"]=body["character_id"]; r["role"]=role; r["style"]=STYLE
    r.animation_data_create(); action=bpy.data.actions.new(name+" • Idle"); r.animation_data.action=action
    for b in r.pose.bones: b.rotation_mode="XYZ"
    for frame,sway in ((1,0),(19,.035),(37,0),(55,-.035),(73,0)):
        r.pose.bones["spine"].rotation_euler[1]=sway; r.pose.bones["spine"].keyframe_insert(data_path="rotation_euler",frame=frame)
        r.pose.bones["head"].rotation_euler[2]=math.sin(frame/72*math.tau)*.035; r.pose.bones["head"].keyframe_insert(data_path="rotation_euler",frame=frame)
    try:
        for fc in action.fcurves:
            for k in fc.keyframe_points: k.interpolation="BEZIER"
            fc.modifiers.new(type="CYCLES")
    except (AttributeError,TypeError): pass
    return {"name":name,"role":role,"rig":r,"mesh":body,"collection":c,"x":0,"y":0}

def look(o,p): o.rotation_euler=(Vector(p)-o.location).to_track_quat("-Z","Y").to_euler()
def env():
    c=coll("LOOMGLASS • STUDIO"); floor=mat("Atelier floor",(.035,.055,.085),.78,.16); stage=mat("Stage ceramic",(.07,.11,.16),.38,.28)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.05)); bpy.context.object.data.materials.append(floor); bpy.context.object.name="Atelier floor"
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,-.2)); o=bpy.context.object; o.scale=(13.5,21,.25); bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); b=o.modifiers.new("Stage radius","BEVEL"); b.width=.16; b.segments=4; bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=b.name); o.data.materials.append(stage); o.name="Gallery stage"
    def light(n,loc,power,size,color):
        d=bpy.data.lights.new(n,"AREA"); d.energy=power; d.shape="DISK"; d.size=size; d.color=color; a=bpy.data.objects.new(n,d); c.objects.link(a); a.location=loc; look(a,(0,0,1.6))
    light("Warm key",(4,-6,8),1250,5,(1,.79,.61)); light("Cool fill",(-5,-4,4.5),780,4.5,(.48,.72,1)); light("Mint rim",(1,4,6.5),1550,3,(.35,1,.85)); light("Face bounce",(0,-4,2.7),260,2.3,(1,.88,.72))
    d=bpy.data.cameras.new("Loomglass review camera"); cam=bpy.data.objects.new("Loomglass review camera",d); c.objects.link(cam); cam.data.type="ORTHO"; cam.data.ortho_scale=6.45; cam.location=(4.1,-8.8,4); look(cam,(0,0,1.72)); bpy.context.scene.camera=cam
    world=bpy.data.worlds.new("Loomglass atelier world"); world.use_nodes=True; world.node_tree.nodes["Background"].inputs["Color"].default_value=(.018,.027,.052,1); world.node_tree.nodes["Background"].inputs["Strength"].default_value=.38; bpy.context.scene.world=world
    return cam,c

def export_glb(ch,path):
    r,m=ch["rig"],ch["mesh"]; x,y=r.location.x,r.location.y; r.location=(0,0,0); bpy.ops.object.select_all(action="DESELECT"); r.select_set(True); m.select_set(True); bpy.context.view_layer.objects.active=r
    bpy.ops.export_scene.gltf(filepath=str(path),export_format="GLB",use_selection=True,export_animations=True,export_skins=True,export_cameras=False,export_lights=False,export_materials="EXPORT")
    r.location=(x,y); bpy.ops.object.select_all(action="DESELECT")

def main():
    a=args(); out=Path(a.output_dir).resolve(); (out/"characters").mkdir(parents=True,exist_ok=True); (out/"previews").mkdir(exist_ok=True)
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene; scene.render.engine="CYCLES"; scene.cycles.device="CPU"; scene.cycles.samples=max(8,a.samples); scene.cycles.use_denoising=True; scene.render.resolution_x=W; scene.render.resolution_y=H; scene.render.resolution_percentage=100; scene.render.image_settings.file_format="PNG"; scene.render.image_settings.color_mode="RGBA"; scene.render.fps=FPS; scene.frame_start=1; scene.frame_end=END; scene.view_settings.view_transform="AgX"
    chars=[build(s,i+1) for i,s in enumerate(CAST)]; cam,studio=env(); glbs=[]
    for ch in chars:
        p=out/"characters"/(ch["name"]+".glb"); export_glb(ch,p); glbs.append(p)
    prev=[]
    for ch in chars:
        hidden={x["mesh"].name:x["mesh"].hide_render for x in chars}; old=[(x["rig"].location.x,x["rig"].location.y) for x in chars]
        for x in chars: x["mesh"].hide_render=(x is not ch)
        ch["rig"].location=(0,0,0); cam.location=(4.1,-8.8,4); look(cam,(0,0,1.72)); cam.data.ortho_scale=7.6; scene.frame_set(19); p=out/"previews"/(ch["name"]+"_720p.png"); scene.render.filepath=str(p); bpy.ops.render.render(write_still=True); prev.append(p)
        for x,(xx,yy) in zip(chars,old): x["rig"].location=(xx,yy,0); x["mesh"].hide_render=hidden[x["mesh"].name]
    for i,ch in enumerate(chars):
        col=i%5; row=i//5; x=(col-2)*2.55; y=3.8 if row==0 else -3.8; ch["rig"].location=(x,y,0); ch["x"],ch["y"]=x,y
    cam.location=(0,-20,15); look(cam,(0,0,1.48)); cam.data.ortho_scale=16.4; scene.frame_set(1); gallery=out/"GAMEFORGE_LOOMGLASS_Gallery_1280x720.png"; scene.render.filepath=str(gallery); bpy.ops.render.render(write_still=True)
    blend=out/"GAMEFORGE_LOOMGLASS_10_Character_Lab.blend"; bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    report={"project":"GAMEFORGE 10-character test","style":STYLE,"renderer":"Blender Cycles CPU","resolution":[W,H],"samples":scene.cycles.samples,"fps":FPS,"idle_frames":END,"image_generation":False,"characters":[],"failures":[]}
    for ch,g,p in zip(chars,glbs,prev):
        m,r=ch["mesh"],ch["rig"]; checks={"rig":r.type=="ARMATURE","single_mesh":m.type=="MESH" and bool(m.get("single_unified_mesh")),"armature_modifier":any(x.type=="ARMATURE" and x.object==r for x in m.modifiers),"weighted_vertices":all(bool(v.groups) for v in m.data.vertices),"17_bones":len(r.data.bones)==17,"idle_action":bool(r.animation_data and r.animation_data.action),"glb":g.exists() and g.stat().st_size>5000,"720p_preview":p.exists()}
        bad=[k for k,v in checks.items() if not v]; report["failures"] += [ch["name"]+":"+k for k in bad]; report["characters"].append({"name":ch["name"],"role":ch["role"],"vertices":len(m.data.vertices),"bones":len(r.data.bones),"glb_bytes":g.stat().st_size if g.exists() else 0,"checks":checks})
    (out/"GAMEFORGE_LOOMGLASS_Audit.json").write_text(json.dumps(report,indent=2))
    if report["failures"]: raise RuntimeError("Character audit failed: "+str(report["failures"]))
    (out/"README.md").write_text("# GAMEFORGE Loomglass character test\n\nTen procedurally modelled, 17-bone rigged Blender characters. Each GLB contains one skinned mesh and an idle animation. Ten individual previews and one 1280x720 gallery render are included. Native Blender Cycles CPU, denoised. No image generation or external models.\n")
    pack=out/"GAMEFORGE_LOOMGLASS_10_Character_Review_Pack.zip"
    with zipfile.ZipFile(pack,"w",zipfile.ZIP_DEFLATED,6) as z:
        for p in out.rglob("*"):
            if p.is_file() and p!=pack: z.write(p,p.relative_to(out.parent))
    print(json.dumps({"characters":len(chars),"gallery":str(gallery),"blend":str(blend),"zip":str(pack),"audit":str(out/"GAMEFORGE_LOOMGLASS_Audit.json"),"failures":report["failures"]},indent=2),flush=True)
if __name__=="__main__": main()
