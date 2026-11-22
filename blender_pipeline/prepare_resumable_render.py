#!/usr/bin/env python3
"""Prepare FrameForge's Blender scene for resumable 3-second CPU rendering."""
from pathlib import Path
p=Path("blender_pipeline/phishing_explainer.py")
s=p.read_text(encoding="utf-8")

def once(old,new,label):
    global s
    if old not in s:
        if new in s: return
        raise SystemExit(label+": source pattern not found")
    if s.count(old)!=1: raise SystemExit(label+": source pattern is not unique")
    s=s.replace(old,new,1)

once('world.color=PAL["void"]','world.color=PAL["void"][:3]',"RGB world colour")

old15="SEGMENT_SECONDS = 15\nSEGMENT_FRAMES = FPS * SEGMENT_SECONDS\nSTAGE_COUNT = 8"
old3="SEGMENT_SECONDS = 3\nSEGMENT_FRAMES = FPS * SEGMENT_SECONDS\nSTAGE_COUNT = 8\nRENDER_CHUNK_COUNT = (TOTAL_FRAMES + SEGMENT_FRAMES - 1) // SEGMENT_FRAMES"
new_constants="STAGE_SECONDS = 15\nSTAGE_FRAMES = FPS * STAGE_SECONDS\nRENDER_CHUNK_SECONDS = 3\nRENDER_CHUNK_FRAMES = FPS * RENDER_CHUNK_SECONDS\nSTAGE_COUNT = 8\nRENDER_CHUNK_COUNT = (TOTAL_FRAMES + RENDER_CHUNK_FRAMES - 1) // RENDER_CHUNK_FRAMES"
if old15 in s: s=s.replace(old15,new_constants,1)
elif old3 in s: s=s.replace(old3,new_constants,1)
elif new_constants not in s: raise SystemExit("stage/chunk constants are unknown")

for old,new,label in [
 ("start=stage*SEGMENT_FRAMES+state*150+1","start=stage*STAGE_FRAMES+state*150+1","sprite timing"),
 ("frame=i*SEGMENT_FRAMES+int(sec*FPS)+1","frame=i*STAGE_FRAMES+int(sec*FPS)+1","camera timing"),
 ("a=i*SEGMENT_FRAMES+1; b=min(a+SEGMENT_FRAMES-1,TOTAL_FRAMES)","a=i*STAGE_FRAMES+1; b=min(a+STAGE_FRAMES-1,TOTAL_FRAMES)","packet timing"),
 ("frame=a+SEGMENT_FRAMES//2","frame=a+STAGE_FRAMES//2","packet midpoint")]:
    if old in s: s=s.replace(old,new,1)
    elif new not in s: raise SystemExit(label+": unknown stage frame reference")

once('safe_set(scene.eevee,"taa_render_samples",64)','safe_set(scene.eevee,"taa_render_samples",16)',"EEVEE samples")
once('safe_set(scene.render,"use_motion_blur",True)\n    safe_set(scene.render,"motion_blur_shutter",0.28)',
      'safe_set(scene.render,"use_motion_blur",False)',"motion blur")
compositor='''    # Subtle glow pass for emissive neon elements.
    scene.use_nodes=True
    nt=scene.node_tree; nt.nodes.clear()
    rl=nt.nodes.new("CompositorNodeRLayers")
    glare=nt.nodes.new("CompositorNodeGlare"); glare.glare_type="FOG_GLOW"
    safe_set(glare,"threshold",1.5); safe_set(glare,"quality","MEDIUM")
    comp=nt.nodes.new("CompositorNodeComposite")
    nt.links.new(rl.outputs["Image"],glare.inputs["Image"])
    nt.links.new(glare.outputs["Image"],comp.inputs["Image"])
'''
if compositor in s:
    s=s.replace(compositor,"    # Emissive materials retain the neon look without a legacy compositor pass.\n",1)
elif "scene.node_tree" in s:
    raise SystemExit("unrecognised Blender compositor setup")

light_old='o.data.energy=power; o.data.shape="DISK"; o.data.size=size; o.data.color=col\n            o.rotation_euler='
light_new='o.data.energy=power; o.data.shape="DISK"; o.data.size=size; o.data.color=col\n            safe_set(o.data,"use_shadow",n=="Cool overhead softbox")\n            o.rotation_euler='
once(light_old,light_new,"light shadow settings")

pack_old='    project=os.path.join(outdir,OUT_NAME+".blend")\n    bpy.ops.wm.save_as_mainfile(filepath=project)'
pack_new='    project=os.path.join(outdir,OUT_NAME+".blend")\n    try: bpy.ops.file.pack_all()\n    except Exception as exc: print("PACK_IMAGES_WARNING",exc,flush=True)\n    bpy.ops.wm.save_as_mainfile(filepath=project)'
once(pack_old,pack_new,"pack scene textures")

project_arg='    p.add_argument("--output-dir", default="output/phishing_explainer")\n    p.add_argument("--project", default="", help="Packed Blender project from audit")'
if 'p.add_argument("--project"' not in s:
    once('    p.add_argument("--output-dir", default="output/phishing_explainer")',project_arg,"project CLI option")

if "def render_segment(scene,seg,outdir):\n    \"\"\"Render one short checkpoint" not in s:
    a=s.index("def render_segment(scene,seg,outdir):")
    b=s.index("\n\ndef main():",a)
    renderer='''def render_segment(scene,seg,outdir):
    """Render one 90-frame checkpoint for independent upload and retry."""
    if seg<0 or seg>=RENDER_CHUNK_COUNT:
        raise ValueError(f"segment-index must be 0..{RENDER_CHUNK_COUNT-1}")
    os.makedirs(outdir,exist_ok=True)
    start=seg*RENDER_CHUNK_FRAMES+1
    end=min(start+RENDER_CHUNK_FRAMES-1,TOTAL_FRAMES)
    count=end-start+1
    frame_dir=os.path.join(outdir,f"chunk_{seg:02d}_frames")
    os.makedirs(frame_dir,exist_ok=True)
    prefix=os.path.join(frame_dir,"frame_")
    scene.render.filepath=prefix
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGBA"
    scene.render.image_settings.color_depth="8"
    scene.render.resolution_x=WIDTH; scene.render.resolution_y=HEIGHT
    scene.render.resolution_percentage=100; scene.render.fps=FPS
    scene.frame_start=start; scene.frame_end=end; scene.frame_set(start)
    print("PHISHING_CHUNK_START",seg,start,end,WIDTH,HEIGHT,"samples=16",flush=True)
    bpy.ops.render.render(animation=True)
    path=os.path.join(outdir,f"chunk_{seg:02d}.mp4")
    cmd=["ffmpeg","-y","-framerate",str(FPS),"-start_number",str(start),"-i",prefix+"%04d.png",
         "-frames:v",str(count),"-c:v","libx264","-preset","veryfast","-crf","18",
         "-pix_fmt","yuv420p","-movflags","+faststart",path]
    subprocess.run(cmd,check=True)
    if not os.path.exists(path) or os.path.getsize(path)<50000:
        raise RuntimeError("Missing or undersized checkpoint: "+path)
    print("PHISHING_CHUNK_VERIFIED",path,count,os.path.getsize(path),flush=True)
'''
    s=s[:a]+renderer+s[b:]

old_main='''def main():
    a=parse_args()
    root=os.path.dirname(os.path.abspath(__file__))
    cover=os.path.join(root,"assets","cyberspace_unlocked_cover.jpg")
    scene,sprites,moving=build_scene(root,cover,a.output_dir)
    if a.mode=="audit": audit(scene,sprites,moving,a.output_dir)
    else: render_segment(scene,a.segment_index,a.output_dir)
'''
new_main='''def main():
    a=parse_args()
    if a.mode=="audit":
        root=os.path.dirname(os.path.abspath(__file__))
        cover=os.path.join(root,"assets","cyberspace_unlocked_cover.jpg")
        scene,sprites,moving=build_scene(root,cover,a.output_dir)
        audit(scene,sprites,moving,a.output_dir)
        return
    if a.project:
        if not os.path.isfile(a.project): raise FileNotFoundError(a.project)
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.project))
        scene=bpy.context.scene
        if scene.camera is None: raise RuntimeError("Audited scene has no active camera")
        print("OPENED_AUDITED_SCENE",a.project,"objects",len(bpy.data.objects),flush=True)
    else:
        root=os.path.dirname(os.path.abspath(__file__))
        cover=os.path.join(root,"assets","cyberspace_unlocked_cover.jpg")
        scene,_,_=build_scene(root,cover,a.output_dir)
    render_segment(scene,a.segment_index,a.output_dir)
'''
once(old_main,new_main,"main render entrypoint")
p.write_text(s,encoding="utf-8")
print("RESUMABLE_RENDER_PATCH_APPLIED",len(s),"characters; chunks",RENDER_CHUNK_COUNT if "RENDER_CHUNK_COUNT" in globals() else 40)
