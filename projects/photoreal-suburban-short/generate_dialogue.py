#!/usr/bin/env python3
"""Create a 30-second two-speaker dialogue track for the suburban Three.js short."""
from __future__ import annotations
import json, shutil, subprocess, tempfile
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from kokoro import KPipeline

SR = 24000
TOTAL = 30.0
MODEL = "hexgrad/Kokoro-82M"
SEGMENTS = [
    {"speaker":"driver_sedan","voice":"am_echo","start":2.0,"duration":5.8,
     "text":"This road feels quieter than I expected. The new houses look beautiful."},
    {"speaker":"driver_suv","voice":"af_bella","start":8.0,"duration":6.2,
     "text":"The school rush is over. I like how they kept the trees along the street."},
    {"speaker":"driver_sedan","voice":"am_echo","start":16.0,"duration":5.8,
     "text":"Look at the brickwork and the roof tiles. They even added proper driveways."},
    {"speaker":"driver_suv","voice":"af_bella","start":22.2,"duration":6.0,
     "text":"And the sidewalks are finally smooth. This neighbourhood feels calm again."},
]

def run(args):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if p.returncode:
        raise RuntimeError(f"Command failed: {' '.join(args)}\n{p.stderr[-5000:]}")

def synth(pipe, text, voice):
    chunks=[]
    for _graphemes, _phonemes, audio in pipe(text, voice=voice, speed=1.0):
        if audio is None: continue
        if hasattr(audio,"detach"): audio=audio.detach().cpu().numpy()
        chunk=np.asarray(audio,dtype=np.float32).reshape(-1)
        if chunk.size: chunks.append(chunk)
    if not chunks: raise RuntimeError(f"Kokoro returned no audio for voice {voice}")
    out=np.concatenate(chunks)
    if not np.isfinite(out).all(): raise RuntimeError("Non-finite audio")
    return out

def fit(audio, duration, temp, label):
    src=temp/f"{label}-raw.wav"; dst=temp/f"{label}-fit.wav"
    sf.write(src,audio,SR,subtype="PCM_16")
    src_duration=len(audio)/SR
    tempo=src_duration/duration
    if not 0.55 <= tempo <= 1.75:
        raise RuntimeError(f"{label} requires extreme speech tempo {tempo:.2f}; refusing.")
    run(["ffmpeg","-y","-v","error","-i",str(src),"-af",
         f"atempo={tempo:.8f},apad=whole_dur={duration:.6f},atrim=duration={duration:.6f}",
         "-ar",str(SR),"-ac","1","-c:a","pcm_s16le",str(dst)])
    x,sr=sf.read(dst,dtype="float32")
    if sr!=SR: raise RuntimeError("Unexpected sample rate")
    x=np.asarray(x,dtype=np.float32).reshape(-1)
    n=round(duration*SR)
    x=x[:n] if len(x)>n else np.pad(x,(0,n-len(x)))
    fade=min(round(0.014*SR),len(x)//4)
    if fade:
        x[:fade]*=np.linspace(0,1,fade,dtype=np.float32)
        x[-fade:]*=np.linspace(1,0,fade,dtype=np.float32)
    return x, tempo, src_duration

def main():
    if not shutil.which("ffmpeg"): raise SystemExit("ffmpeg missing")
    torch.set_num_threads(max(1,min(4,torch.get_num_threads())))
    output=Path("projects/photoreal-suburban-short/output")
    output.mkdir(parents=True,exist_ok=True)
    print(f"Loading {MODEL} for Kokoro two-speaker dialogue",flush=True)
    pipe=KPipeline(lang_code="a")
    pcm=np.zeros(round(TOTAL*SR),dtype=np.float32)
    records=[]
    with tempfile.TemporaryDirectory(prefix="frameforge-suburban-") as td:
        td=Path(td)
        for i,seg in enumerate(SEGMENTS):
            print(f"Synthesizing {seg['speaker']} with {seg['voice']}",flush=True)
            audio=synth(pipe,seg["text"],seg["voice"])
            fitted,tempo,source_duration=fit(audio,seg["duration"],td,f"line-{i+1}")
            start=round(seg["start"]*SR); end=start+len(fitted)
            if start<0 or end>len(pcm): raise RuntimeError("Dialogue segment exceeds 30 seconds")
            pcm[start:end]+=fitted
            records.append({**seg,"end":seg["start"]+seg["duration"],"source_duration":source_duration,"fit_atempo":tempo})
    peak=float(np.max(np.abs(pcm)))
    if peak>0.98: pcm*=0.98/peak
    wav=output/"suburban-dialogue.wav"
    mp3=output/"suburban-dialogue.mp3"
    sf.write(wav,pcm,SR,subtype="PCM_16")
    run(["ffmpeg","-y","-v","error","-i",str(wav),"-map_metadata","-1","-codec:a","libmp3lame","-b:a","160k","-ar",str(SR),"-ac","1",str(mp3)])
    duration=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(mp3)],text=True).strip())
    if not 29.90<=duration<=30.12: raise RuntimeError(f"MP3 duration {duration:.3f}s is not 30s")
    data={"status":"PASS","model":MODEL,"sample_rate":SR,"channels":1,"duration_seconds":duration,"voices":["Kokoro Echo (am_echo)","Kokoro Bella (af_bella)"],"segments":records}
    (output/"suburban-dialogue-timing.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(data,indent=2),flush=True)

if __name__=="__main__": main()
