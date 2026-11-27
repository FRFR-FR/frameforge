#!/usr/bin/env python3
"""Generate the 30s FrameForge mechanical-watch narration and a shared TTS sample.

Voice: Kokoro Echo (am_echo), US English. No voice fallback is permitted.
The script uses three fixed segments so the spoken CTA begins at exactly 10.00s.
"""
from __future__ import annotations
import argparse, json, shutil, subprocess, tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from kokoro import KPipeline

VOICE = "am_echo"
MODEL = "hexgrad/Kokoro-82M"
SAMPLE_RATE = 24000
TOTAL = 30.0
SAMPLE_TEXT = "This tiny balance wheel swings back and forth, keeping a mechanical watch ticking with remarkable precision."
SEGMENTS = [
    {"id":"opening","start":0.0,"duration":10.0,
     "text":"A mechanical watch turns one wound spring into every second. Inside, a steel mainspring stores energy, not electricity. Tiny gears carry that power forward without a battery."},
    {"id":"cta","start":10.0,"duration":7.0/2.7,
     "text":"Like and subscribe for more tiny engineering."},
    {"id":"explanation","start":10.0+7.0/2.7,"duration":30.0-10.0-7.0/2.7,
     "text":"At the center, an escapement releases one tooth at a time. A balance wheel and hairspring swing back and forth, setting the rhythm. The gear train turns that steady beat into the minute and hour hands. No battery, no screen, just stored energy, carefully metered into motion."},
]

def run(args):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if p.returncode: raise RuntimeError(f"Command failed: {' '.join(args)}\n{p.stderr[-6000:]}")

def synth(pipeline,text):
    chunks=[]
    for _g,_p,a in pipeline(text,voice=VOICE,speed=1.0):
        if a is not None:
            if hasattr(a,"detach"): a=a.detach().cpu().numpy()
            q=np.asarray(a,dtype=np.float32).reshape(-1)
            if q.size: chunks.append(q)
    if not chunks: raise RuntimeError("Kokoro Echo returned no audio; no substitute voice will be used.")
    out=np.concatenate(chunks)
    if not np.isfinite(out).all(): raise RuntimeError("Non-finite audio returned.")
    return out

def fit(audio,duration,tmp,label):
    src=tmp/f"{label}-raw.wav"; dst=tmp/f"{label}-fit.wav"
    sf.write(src,audio,SAMPLE_RATE,subtype="PCM_16")
    src_dur=len(audio)/SAMPLE_RATE; tempo=src_dur/duration
    if not .5<=tempo<=2.0: raise RuntimeError(f"{label} pacing would require atempo={tempo:.2f}; refusing extreme speech speed.")
    run(["ffmpeg","-y","-v","error","-i",str(src),"-af",
         f"atempo={tempo:.8f},apad=whole_dur={duration:.6f},atrim=duration={duration:.6f}",
         "-ar",str(SAMPLE_RATE),"-ac","1","-c:a","pcm_s16le",str(dst)])
    x,sr=sf.read(dst,dtype="float32")
    if sr!=SAMPLE_RATE: raise RuntimeError("Unexpected output sample rate.")
    x=np.asarray(x,dtype=np.float32).reshape(-1)
    n=round(duration*SAMPLE_RATE)
    if len(x)>n: x=x[:n]
    if len(x)<n: x=np.pad(x,(0,n-len(x)))
    fade=min(round(.012*SAMPLE_RATE),len(x)//4)
    if fade:
        x[:fade]*=np.linspace(0,1,fade,dtype=np.float32)
        x[-fade:]*=np.linspace(1,0,fade,dtype=np.float32)
    return x

def mp3(wav,mp3):
    run(["ffmpeg","-y","-v","error","-i",str(wav),"-map_metadata","-1","-codec:a","libmp3lame","-b:a","160k","-ar",str(SAMPLE_RATE),"-ac","1",str(mp3)])

def duration(path):
    p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if p.returncode: raise RuntimeError(p.stderr)
    return float(p.stdout.strip())

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",default="projects/mechanical-watch-narrative/output")
    a=ap.parse_args()
    for exe in ("ffmpeg","ffprobe"):
        if not shutil.which(exe): raise SystemExit(f"Missing {exe}")
    torch.set_num_threads(max(1,min(4,torch.get_num_threads())))
    out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    print(f"Loading {MODEL}; voice={VOICE}",flush=True)
    pipe=KPipeline(lang_code="a")
    with tempfile.TemporaryDirectory(prefix="frameforge-watch-echo-") as td:
        td=Path(td)
        parts=[]
        for seg in SEGMENTS:
            print("Synthesizing",seg["id"],flush=True)
            parts.append(fit(synth(pipe,seg["text"]),seg["duration"],td,seg["id"]))
        pcm=np.concatenate(parts)
        if len(pcm)!=TOTAL*SAMPLE_RATE: raise RuntimeError(f"Expected 720000 samples, got {len(pcm)}")
        wav=out/"watch-narration-echo.wav"; mp=out/"watch-narration-echo.mp3"
        sf.write(wav,pcm,SAMPLE_RATE,subtype="PCM_16"); mp3(wav,mp)
        sample=synth(pipe,SAMPLE_TEXT)
        sample_wav=out/"watch-tts-sample-kokoro-echo.wav"; sample_mp3=out/"watch-tts-sample-kokoro-echo.mp3"
        sf.write(sample_wav,sample,SAMPLE_RATE,subtype="PCM_16"); mp3(sample_wav,sample_mp3)
    d=duration(mp)
    if not 29.90<=d<=30.15: raise RuntimeError(f"Narration MP3 duration is {d:.3f}s")
    info={"status":"PASS","voice":"Kokoro Echo (am_echo)","model":MODEL,"duration_seconds":d,
          "wav_samples":int(len(pcm)),"sample_rate":SAMPLE_RATE,"channels":1,"bitrate":"160 kbps",
          "cta_start_seconds":10.0,"spoken_word_count":81,
          "sample_text":SAMPLE_TEXT}
    (out/"watch-voice-timing.json").write_text(json.dumps(info,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(info,indent=2),flush=True)
if __name__=="__main__": main()
