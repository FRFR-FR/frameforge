#!/usr/bin/env python3
"""Footage-first 720p-only master renderer for EP002. No text, captions or subtitles."""
from pathlib import Path
import csv,json,math,shutil,subprocess,sys,os
ROOT=Path(__file__).resolve().parent; OUT=ROOT/"output"; ASSETS=ROOT/"assets"/"broll"
FPS=24
CUTS={"section_04":"scene_04_tin_plasma","section_05":"scene_05_mirror_optics","section_06":"scene_06_reticle_projection","section_07":"scene_07_wafer_stage","section_08":"scene_08_layer_stack"}
def run(cmd): subprocess.run(cmd,check=True)
def probe(p): return json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(p)],text=True))
def duration(p): return float(probe(p)["format"]["duration"])
def validate(p):
 m=probe(p); v=next((s for s in m["streams"] if s.get("codec_type")=="video"),None)
 if not v or int(v.get("width",0))<1280 or int(v.get("height",0))<720: raise RuntimeError("Source B-roll must contain at least 1280x720 video: "+str(p))
 if duration(p)<7: raise RuntimeError("B-roll clip shorter than 7 seconds: "+str(p))
 run(["ffmpeg","-v","error","-i",str(p),"-f","null","-"])
def encode(src,dest,secs,seek):
 vf="scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1,fps=24,format=yuv420p"
 run(["ffmpeg","-hide_banner","-loglevel","error","-y","-ss",str(seek),"-stream_loop","-1","-i",str(src),"-t",str(secs),"-vf",vf,"-an","-c:v","libx264","-preset","veryfast","-crf","20","-profile:v","high","-pix_fmt","yuv420p","-r","24","-g","48","-movflags","+faststart",str(dest)])
def main():
 OUT.mkdir(exist_ok=True,parents=True)
 arpath=OUT/"kokoro_narration_report.json"
 if not arpath.exists(): raise RuntimeError("Kokoro narration report missing; no silent voice substitution.")
 ar=json.loads(arpath.read_text()); assert ar.get("provider")=="Kokoro-82M" and ar.get("voice_id")=="am_echo"
 wav=OUT/ar["wav"]; assert wav.is_file() and wav.stat().st_size>10000
 audio_seconds=duration(wav)
 if not 480<=audio_seconds<=720: raise RuntimeError("Narration length outside 8–12 minutes; revise naturally, do not pad.")
 sections=ar.get("sections",[])
 if len(sections)!=10: raise RuntimeError("Expected ten narration sections.")
 manifest=ROOT/"asset-manifest-broll.csv"
 if not manifest.is_file(): raise RuntimeError("Missing per-asset rights manifest.")
 clipmap={}; count=0
 for sec in sections:
  clips=sorted((ASSETS/sec["id"]).glob("*.mp4"))
  if len(clips)<3: raise RuntimeError(sec["id"]+" requires at least 3 unique relevant clips.")
  for p in clips: validate(p)
  clipmap[sec["id"]]=clips; count+=len(clips)
 if count<27: raise RuntimeError("Need at least 27 unique B-roll clips.")
 blender=shutil.which("blender")
 if not blender: raise RuntimeError("Blender executable missing; cannot render original 3D cutaways.")
 frames=OUT/"3d_frames"; frames.mkdir(exist_ok=True)
 run([blender,"--background","--factory-startup","--python",str(ROOT/"scripts"/"generate_3d_cutaways.py"),"--","--output-dir",str(frames)])
 cutclips={}
 for folder in sorted(frames.glob("scene_*")):
  pngs=sorted(folder.glob("frame_*.png"))
  if len(pngs)!=120: raise RuntimeError(folder.name+" did not produce 120 frames.")
  dest=OUT/"3d_clips"/(folder.name+".mp4"); dest.parent.mkdir(exist_ok=True)
  run(["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate","24","-start_number","1","-i",str(folder/"frame_%04d.png"),"-frames:v","120","-vf","scale=1280:720:flags=lanczos,setsar=1,fps=24,format=yuv420p","-an","-c:v","libx264","-preset","veryfast","-crf","20","-profile:v","high","-pix_fmt","yuv420p","-r","24","-g","48",str(dest)])
  cutclips[folder.name]=dest
 if not all(n in cutclips for n in CUTS.values()): raise RuntimeError("A conceptual 3D cutaway did not render.")
 shotdir=OUT/"broll_shots"; shotdir.mkdir(exist_ok=True); concat=[]; timeline=[]; cursor=0; broll_time=0; index=0
 for sec in sections:
  sid=sec["id"]; total=float(sec["duration_seconds"]); cutname=CUTS.get(sid); cutsecs=5 if cutname else 0
  if total<=cutsecs+1: raise RuntimeError(sid+" is too short for its planned cutaway.")
  left=total-cutsecs; clips=clipmap[sid]; n=0
  while left>.01:
   length=min(7,left); src=clips[n%len(clips)]; sd=duration(src); seek=(n*2.13)%max(.1,sd-min(length,sd-.05))
   dst=shotdir/("shot_%05d.mp4"%index); index+=1; encode(src,dst,length,seek); actual=duration(dst); concat.append(dst)
   timeline.append({"start_seconds":round(cursor,3),"duration_seconds":round(actual,3),"section_id":sid,"visual_type":"real-world moving B-roll","source":str(src.relative_to(ROOT))})
   cursor+=actual; broll_time+=actual; left-=length; n+=1
  if cutname:
   p=cutclips[cutname]; actual=duration(p); concat.append(p)
   timeline.append({"start_seconds":round(cursor,3),"duration_seconds":round(actual,3),"section_id":sid,"visual_type":"original conceptual 3D reconstruction, not footage"})
   cursor+=actual
 concatfile=OUT/"concat_timeline.txt"; concatfile.write_text("\\n".join("file '"+p.as_posix().replace("'","'\\\\''")+"'" for p in concat)+"\\n")
 silent=OUT/"temporary_720p_video.mp4"
 run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",str(concatfile),"-fflags","+genpts","-c:v","libx264","-preset","veryfast","-crf","20","-profile:v","high","-pix_fmt","yuv420p","-r","24","-g","48","-an",str(silent)])
 if abs(duration(silent)-audio_seconds)>.35: raise RuntimeError("Video timeline and narration duration differ by more than 0.35 sec.")
 final=OUT/"Underneath_Everything_EP002_720p.mp4"
 run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(silent),"-i",str(wav),"-map","0:v:0","-map","1:a:0","-sn","-c:v","copy","-c:a","aac","-b:a","192k","-ar","48000","-ac","2","-shortest","-movflags","+faststart",str(final)])
 m=probe(final); v=next(s for s in m["streams"] if s["codec_type"]=="video"); a=next(s for s in m["streams"] if s["codec_type"]=="audio")
 if (v["width"],v["height"])!=(1280,720) or v["codec_name"]!="h264" or a["codec_name"]!="aac": raise RuntimeError("Strict 720p H.264/AAC validation failed.")
 measured=v.get("avg_frame_rate","unknown")
 if measured!="24/1": raise RuntimeError("Measured frame rate is "+measured+"; no relabelling is allowed.")
 if a.get("sample_rate")!="48000" or int(a.get("channels",0))!=2: raise RuntimeError("Audio must be stereo AAC 48 kHz.")
 if any(s.get("codec_type")=="subtitle" for s in m["streams"]): raise RuntimeError("Subtitle track is forbidden.")
 runtime=float(m["format"]["duration"])
 if not 480<=runtime<=720: raise RuntimeError("Final runtime outside 8–12 minutes; no padding.")
 run(["ffmpeg","-v","error","-i",str(final),"-f","null","-"])
 coverage=round(100*broll_time/max(runtime,.001),2)
 if coverage<70: raise RuntimeError("Relevant moving B-roll share below 70 percent.")
 run([sys.executable,str(ROOT/"scripts"/"create_thumbnail.py")])
 report={"episode":"EP002","title":"The Machine That Prints the World's Most Advanced Chips","file":final.name,"file_size_bytes":final.stat().st_size,"file_size_mb_decimal":round(final.stat().st_size/1e6,2),"duration_seconds":round(runtime,3),"resolution":"1280x720","fps_measured":measured,"video_codec":v["codec_name"],"audio_codec":a["codec_name"],"audio_sample_rate":a["sample_rate"],"audio_channels":a["channels"],"narration_provider":"Kokoro-82M","narration_voice_id":"am_echo","narration_seconds":round(audio_seconds,3),"broll_assets":count,"broll_seconds":round(broll_time,3),"broll_coverage_percent":coverage,"original_3d_cutaways":sorted(CUTS.values()),"captions":"none","subtitle_streams":"none","visual_text_overlays":"none","thumbnail":"thumbnail_rwb.png","full_decode_check":"PASS","auto_publish":False,"rights_status":"Awaiting human review of every selected asset and full playback."}
 (OUT/"render_report_broll_echo.json").write_text(json.dumps(report,indent=2))
 (OUT/"broll_timeline.json").write_text(json.dumps(timeline,indent=2))
 print(json.dumps(report,indent=2))
if __name__=="__main__": main()