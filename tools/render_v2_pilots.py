#!/usr/bin/env python3
"""Procedural FrameForge V2 pilot render generator."""
from __future__ import annotations
import argparse, hashlib, json, math, random, shutil, subprocess, tempfile, wave
from functools import lru_cache
from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H, FPS, DURATION, RATE = 1280, 720, 24, 12, 48000
PILOTS = {
    "entertainment": {"folder":"entertainment-power-scale","title":"Solar Sentinel vs Rift Warden"},
    "cybersecurity": {"folder":"cybersecurity-phishing-check","title":"Pause. Check. Verify. Report."}
}
BACKGROUNDS = {}

@lru_cache(maxsize=24)
def font(size, bold=True):
    candidates = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                  "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"]
    for item in candidates:
        if Path(item).is_file():
            return ImageFont.truetype(item, size)
    return ImageFont.load_default()

def blend(a,b,t):
    return round(a+(b-a)*max(0,min(1,t)))

def background(pilot):
    if pilot in BACKGROUNDS: return BACKGROUNDS[pilot]
    top,bottom = ((8,13,28),(23,20,46)) if pilot=="entertainment" else ((7,19,34),(10,34,50))
    image=Image.new("RGB",(W,H)); px=image.load()
    for y in range(H):
        c=tuple(blend(top[i],bottom[i],y/(H-1)) for i in range(3))
        for x in range(W): px[x,y]=c
    d=ImageDraw.Draw(image,"RGBA")
    col=(128,145,185,17) if pilot=="entertainment" else (100,190,220,18)
    for x in range(0,W,64): d.line((x,0,x,H),fill=col)
    for y in range(0,H,64): d.line((0,y,W,y),fill=col)
    BACKGROUNDS[pilot]=image
    return image

def label(d,xy,value,size=16,fill=(230,240,255,255),anchor=None,bold=True):
    d.text(xy,value,font=font(size,bold),fill=fill,anchor=anchor)

def chip(d,x,y,value,color,width=210):
    d.rounded_rectangle((x,y,x+width,y+38),radius=16,fill=(16,25,43,240),outline=(*color,210),width=2)
    label(d,(x+width//2,y+19),value,13,(*color,255),"mm")

def particles(d,frame,color,seed=23,count=45):
    rng=random.Random(seed)
    for i in range(count):
        x0=rng.randrange(20,W-20); y0=rng.randrange(40,H-30); speed=rng.uniform(.35,1.8)
        x=int((x0+frame*speed*(1 if i%2 else -1))%W); y=int((y0-frame*speed)%H)
        r=rng.choice((1,2,2,3))
        d.ellipse((x-r,y-r,x+r,y+r),fill=(*color,rng.randrange(90,220)))

def aura(image,xy,radius,color):
    layer=Image.new("RGBA",image.size,(0,0,0,0)); d=ImageDraw.Draw(layer)
    x,y=xy
    for r,a in ((radius,18),(int(radius*.7),22),(int(radius*.42),25)):
        d.ellipse((x-r,y-r,x+r,y+r),fill=(*color,a))
    layer=layer.filter(ImageFilter.GaussianBlur(radius//3))
    return Image.alpha_composite(image.convert("RGBA"),layer)

def sentinel(d,cx,cy,t,s=1):
    cy=int(cy+math.sin(t*3.2)*7)
    p=lambda points:[(int(cx+x*s),int(cy+y*s)) for x,y in points]
    d.ellipse((cx-104*s,cy-220*s,cx+104*s,cy-8*s),outline=(255,208,118,150),width=max(2,int(s*4)))
    d.polygon(p([(-55,-80),(55,-80),(110,130),(20,94),(-25,150),(-112,115)]),fill=(167,70,52,255))
    d.polygon(p([(-48,-90),(48,-90),(72,46),(0,94),(-72,46)]),fill=(243,164,57,255),outline=(255,220,146,255))
    d.polygon(p([(-52,-68),(-103,18),(-79,35),(-22,-32)]),fill=(255,184,72,255))
    d.polygon(p([(52,-68),(108,9),(86,32),(22,-32)]),fill=(255,184,72,255))
    d.polygon(p([(-27,48),(-4,52),(-28,166),(-59,164)]),fill=(235,158,62,255))
    d.polygon(p([(4,52),(29,48),(63,162),(32,169)]),fill=(235,158,62,255))
    d.ellipse((cx-48*s,cy-184*s,cx+48*s,cy-93*s),fill=(248,188,82,255),outline=(255,230,166,255),width=3)
    d.polygon(p([(-48,-156),(-18,-200),(31,-190),(52,-147),(26,-130),(-30,-132)]),fill=(255,219,143,255))
    d.polygon(p([(-30,-155),(31,-155),(25,-139),(-26,-139)]),fill=(50,55,78,255))
    d.ellipse((cx-12*s,cy-54*s,cx+12*s,cy-30*s),fill=(255,247,195,255))

def warden(d,cx,cy,t,s=1):
    cy=int(cy+math.sin(t*2.6+1.4)*9)
    p=lambda points:[(int(cx+x*s),int(cy+y*s)) for x,y in points]
    d.ellipse((cx-112*s,cy-224*s,cx+112*s,cy-3*s),outline=(173,145,255,145),width=max(2,int(s*4)))
    d.polygon(p([(-48,-86),(50,-86),(128,142),(28,111),(0,160),(-28,110),(-128,142)]),fill=(47,42,91,255),outline=(133,116,218,255))
    d.polygon(p([(-53,-87),(53,-87),(72,45),(0,95),(-72,45)]),fill=(89,75,153,255),outline=(185,173,255,255))
    d.polygon(p([(-48,-58),(-109,4),(-83,27),(-18,-28)]),fill=(103,91,181,255))
    d.polygon(p([(48,-58),(110,4),(83,27),(18,-28)]),fill=(103,91,181,255))
    d.polygon(p([(-43,47),(-10,54),(-40,165),(-67,164)]),fill=(59,54,106,255))
    d.polygon(p([(10,54),(43,47),(67,165),(39,165)]),fill=(59,54,106,255))
    d.ellipse((cx-49*s,cy-189*s,cx+49*s,cy-91*s),fill=(67,61,115,255),outline=(196,179,255,255),width=3)
    d.polygon(p([(-49,-155),(-55,-188),(-19,-211),(18,-202),(54,-166),(40,-133),(0,-146),(-40,-132)]),fill=(42,40,76,255),outline=(187,168,255,255))
    d.polygon(p([(-35,-160),(35,-160),(27,-145),(-27,-145)]),fill=(102,221,250,255))
    d.ellipse((cx-12*s,cy-48*s,cx+12*s,cy-24*s),fill=(155,225,255,255))

def power_frame(frame,t):
    image=aura(background("entertainment").copy(),(330,370),250,(255,153,62))
    image=aura(image,(950,370),250,(137,105,255))
    d=ImageDraw.Draw(image,"RGBA"); particles(d,frame,(255,210,135),17); particles(d,frame+13,(160,151,255),83)
    d.rounded_rectangle((38,26,1242,694),radius=26,fill=(8,15,29,168),outline=(76,83,128,120),width=1)
    label(d,(72,48),"FRAMEFORGE  /  ORIGINAL CHARACTER LAB",13,(169,181,207,255))
    chip(d,1030,42,"FICTIONAL MATCHUP",(255,206,130),176)
    if t<2.7:
        q=min(1,max(0,t/1.6)); sentinel(d,int(240+115*q),420,t,1.02); warden(d,int(1040-115*q),420,t,1.02)
        chip(d,120,590,"SOLAR SENTINEL",(255,202,108),260); chip(d,900,590,"RIFT WARDEN",(180,160,255),260)
        label(d,(640,210),"VS",76,(244,241,255,245),"mm")
        label(d,(640,638),"Two original designs. No franchise artwork or borrowed footage.",15,(171,186,210,255),"mm")
    elif t<5.1:
        r=int(90+42*(.5+.5*math.sin(t*8)))
        d.ellipse((640-r,352-r,640+r,352+r),outline=(255,227,164,225),width=7)
        d.ellipse((640-r//2,352-r//2,640+r//2,352+r//2),outline=(172,152,255,220),width=5)
        sentinel(d,320,435,t,.78); warden(d,960,435,t,.78)
        label(d,(640,350),"MATCHUP",21,(246,242,255,255),"mm")
        label(d,(640,626),"A comparison only makes sense after the conditions are defined.",17,(193,204,223,255),"mm")
    elif t<8.7:
        label(d,(86,111),"COMPARE THE SAME CATEGORIES",27)
        label(d,(88,151),"Illustrative profile values — not canon or scientific measurements",14,(160,176,203,255))
        for i,(name,left,right) in enumerate((("POWER",.82,.76),("MOBILITY",.64,.91),("DURABILITY",.88,.71))):
            y=222+i*118; label(d,(92,y),name,15,(208,219,241,255))
            d.rounded_rectangle((340,y-4,810,y+27),radius=14,fill=(33,40,61,255))
            d.rounded_rectangle((340,y-4,340+int(470*left),y+27),radius=14,fill=(255,182,79,255))
            d.rounded_rectangle((845,y-4,1230,y+27),radius=14,fill=(33,40,61,255))
            d.rounded_rectangle((845,y-4,845+int(385*right),y+27),radius=14,fill=(155,131,255,255))
            label(d,(323,y+11),"S",15,(255,211,135,255),"mm"); label(d,(831,y+11),"R",15,(195,180,255,255),"mm")
        chip(d,90,590,"S = SENTINEL",(255,202,108),190); chip(d,300,590,"R = WARDEN",(180,160,255),180)
    else:
        label(d,(640,174),"NO UNIVERSAL WINNER",40,(245,244,255,255),"mm")
        label(d,(640,229),"THE SCENARIO DECIDES",29,(255,207,128,255),"mm")
        for i,line in enumerate(("Define the arena and starting distance","State the goal and win conditions","Support claims with evidence","Change the rules, re-check the result")):
            y=305+i*62; d.rounded_rectangle((270,y,1010,y+42),radius=12,fill=(23,36,57,235),outline=(88,112,153,150))
            d.ellipse((295,y+12,313,y+30),fill=(255,197,102,255)); label(d,(334,y+21),line,18,(223,232,247,255),"lm")
        label(d,(640,622),"Original characters • all profile values are illustrative demo values",14,(164,179,204,255),"mm")
    return image.convert("RGB")

def email_card(d,t):
    x,y=108,178
    d.rounded_rectangle((x,y,x+610,y+360),radius=20,fill=(18,35,54,255),outline=(76,122,159,255),width=2)
    d.rounded_rectangle((x,y,x+610,y+56),radius=20,fill=(27,57,82,255))
    d.rectangle((x,y+36,x+610,y+56),fill=(27,57,82,255))
    label(d,(x+28,y+29),"INBOX  /  MESSAGE PREVIEW",15,(191,221,244,255),"lm")
    label(d,(x+28,y+90),"Service Desk",21); label(d,(x+28,y+124),"notify@member-review.example",14,(149,183,211,255))
    label(d,(x+28,y+176),"Subject: Account notice",18)
    label(d,(x+28,y+222),"A routine account message is waiting.",15,(183,199,217,255),bold=False)
    label(d,(x+28,y+256),"Pause before opening unexpected links or files.",14,(183,199,217,255),bold=False)
    d.rounded_rectangle((x+28,y+294,x+260,y+334),radius=10,fill=(25,76,107,255),outline=(86,168,214,255))
    label(d,(x+144,y+314),"INSPECT MESSAGE",13,(230,246,255,255),"mm")
    p=.5+.5*math.sin(t*5); d.rounded_rectangle((x+18,y+107,x+590,y+147),radius=8,fill=(110,40,55,75),outline=(255,int(106+45*p),110,255),width=2)

def cyber_frame(frame,t):
    image=aura(background("cybersecurity").copy(),(965,345),250,(42,154,218))
    image=aura(image,(245,360),190,(238,76,95))
    d=ImageDraw.Draw(image,"RGBA"); particles(d,frame,(92,192,240),77,30)
    d.rounded_rectangle((32,24,1248,696),radius=24,fill=(6,18,31,175),outline=(61,113,145,135))
    label(d,(72,48),"CYBER SAFETY  /  DEFENSIVE WALKTHROUGH",13,(155,200,222,255)); chip(d,1050,40,"SAFE DEMO",(120,226,196),140)
    if t<2.8:
        email_card(d,t)
        d.rounded_rectangle((778,230,1160,310),radius=15,fill=(61,30,42,242),outline=(255,115,119,230),width=2)
        label(d,(968,268),"PAUSE",32,(255,170,169,255),"mm")
        label(d,(968,337),"Unexpected messages deserve a closer look.",16,(204,221,238,255),"mm",False)
        label(d,(640,630),"Fictional message and reserved example address.",14,(148,178,202,255),"mm")
    elif t<5.5:
        email_card(d,t)
        d.rounded_rectangle((770,170,1160,470),radius=20,fill=(15,35,53,248),outline=(83,178,219,220),width=2)
        label(d,(810,211),"CHECK THE SENDER",22,(228,243,255,255))
        label(d,(810,263),"Display name is not proof.",16,(183,207,226,255),bold=False)
        d.rounded_rectangle((807,306,1124,358),radius=9,fill=(77,35,48,255),outline=(255,114,114,220))
        label(d,(965,332),"DOMAIN NEEDS CHECKING",13,(255,185,183,255),"mm")
        label(d,(810,400),"Never trust a sender label alone.",15,(200,216,232,255),bold=False)
        label(d,(640,630),"Check for mismatches, unusual urgency and unexpected files.",14,(148,178,202,255),"mm")
    elif t<8.7:
        label(d,(640,133),"VERIFY THROUGH A ROUTE YOU ALREADY TRUST",27,(233,245,255,255),"mm")
        for i,(x,title,sub,tag) in enumerate(((115,"KNOWN BOOKMARK","Open the official site","WEB"),(485,"TRUSTED CONTACT","Use details you already have","CALL"),(855,"ORGANISATION IT","Follow its reporting process","IT"))):
            d.rounded_rectangle((x,264,x+300,438),radius=18,fill=(17,43,64,245),outline=(67,151,188,220),width=2)
            d.ellipse((x+112,294,x+188,370),fill=(23,90,122,255),outline=(102,210,239,255),width=3)
            label(d,(x+150,332),tag,17,(228,250,255,255),"mm")
            label(d,(x+150,392),title,14,(152,224,245,255),"mm")
            label(d,(x+150,418),sub,12,(199,219,235,255),"mm",False)
            if i<2: label(d,(x+333,350),"→",34,(115,209,243,255),"mm")
        label(d,(640,548),"Do not use contact details supplied by the suspicious message.",17,(255,194,151,255),"mm")
        label(d,(640,630),"Independent verification breaks the message's pressure loop.",14,(148,178,202,255),"mm")
    else:
        label(d,(640,134),"A SIMPLE DEFENSIVE CHECKLIST",34,(235,245,255,255),"mm")
        rows=(("01","PAUSE","Do not rush into the request."),("02","INSPECT","Check sender, wording and unexpected files."),("03","VERIFY","Use an official contact route you know."),("04","REPORT + DELETE","Follow your organisation's reporting process."))
        for i,(number,title,desc) in enumerate(rows):
            y=210+i*85; d.rounded_rectangle((210,y,1070,y+64),radius=13,fill=(14,43,62,242),outline=(62,139,174,165))
            label(d,(250,y+32),number,21,(89,208,235,255),"mm")
            label(d,(300,y+20),title,16,(233,245,255,255))
            label(d,(300,y+45),desc,13,(176,201,221,255),bold=False)
        label(d,(640,586),"Guidance: NIST and CISA • Follow your organisation's policy",14,(129,207,230,255),"mm")
    return image.convert("RGB")

def camera_drift(image,t):
    """Apply a restrained continuous dolly/pan so long graphic beats never become frozen stills."""
    zoom=1.012+0.006*math.sin(t*0.6)
    dx=18*math.sin(t*0.8)
    dy=8*math.cos(t*0.55)
    inverse=1/zoom
    cx,cy=W/2,H/2
    matrix=(inverse,0,cx-(cx+dx)*inverse,0,inverse,cy-(cy+dy)*inverse)
    return image.transform((W,H),Image.Transform.AFFINE,matrix,resample=Image.Resampling.BICUBIC)

def render_frame(pilot,frame,width=W,height=H,fps=FPS):
    if pilot not in PILOTS: raise ValueError("Unknown pilot.")
    if width<1 or height<1 or width>1920 or height>1920: raise ValueError("Preview size out of range.")
    if fps not in (24,25,30) or frame<0 or frame>=DURATION*fps: raise ValueError("Frame or FPS out of range.")
    t=frame/fps
    img=power_frame(frame,t) if pilot=="entertainment" else cyber_frame(frame,t)
    img=camera_drift(img,t)
    return img if img.size==(width,height) else img.resize((width,height),Image.Resampling.LANCZOS)

def create_sfx(path,pilot,duration=DURATION):
    if pilot not in PILOTS or not 0<duration<=30: raise ValueError("Invalid SFX request.")
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    samples=int(RATE*duration); cues=(1.0,3.15,5.4,8.9,10.3) if pilot=="entertainment" else (1.2,3.8,6.1,8.7,10.2)
    rng=random.Random(2701 if pilot=="entertainment" else 2702)
    noise=[rng.uniform(-1,1) for _ in range(samples)]; data=bytearray(); peak=0.0
    for n in range(samples):
        now=n/RATE; value=0.0
        for j,start in enumerate(cues):
            dt=now-start
            if 0<=dt<.34:
                env=math.exp(-dt*(8 if j%2 else 5))
                freq=(440+j*125+260*dt) if pilot=="entertainment" else (520+j*90-180*dt)
                value+=.13*env*math.sin(2*math.pi*freq*dt)+.035*env*noise[n]
        value=max(-.24,min(.24,value)); peak=max(peak,abs(value))
        data.extend(int(value*32767).to_bytes(2,"little",signed=True))
        data.extend(int(value*32767*.92).to_bytes(2,"little",signed=True))
    with wave.open(str(target),"wb") as out:
        out.setnchannels(2); out.setsampwidth(2); out.setframerate(RATE); out.writeframes(data)
    return {"duration_seconds":duration,"sample_rate":RATE,"channels":2,"peak_linear":round(peak,4),"description":"Original synthesized transition/interface cues; no narration voice is bundled."}

def render_pilot(pilot,output_dir,fps=FPS):
    if pilot not in PILOTS or fps not in (24,25,30): raise ValueError("Unsupported pilot or FPS.")
    if not shutil.which("ffmpeg"): raise RuntimeError("FFmpeg is required for MP4 encoding.")
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    folder=ROOT/"projects"/"v2-pilots"/PILOTS[pilot]["folder"]
    project=folder/"project.json"
    if not project.is_file(): raise FileNotFoundError(project)
    audio=out/"original-sfx.wav"; audio_report=create_sfx(audio,pilot)
    count=DURATION*fps
    with tempfile.TemporaryDirectory(prefix="ff-v2-pilot-") as temp:
        frames=Path(temp)
        for i in range(count):
            render_frame(pilot,i,fps=fps).save(frames/f"frame_{i:06d}.png",format="PNG")
        video=out/"pilot.mp4"
        cmd=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y","-framerate",str(fps),"-i",str(frames/"frame_%06d.png"),
             "-i",str(audio),"-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","veryfast","-crf","20",
             "-pix_fmt","yuv420p","-threads","2","-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",str(video)]
        result=subprocess.run(cmd,capture_output=True,text=True,check=False)
        if result.returncode: raise RuntimeError("FFmpeg failed: "+result.stderr[-4000:])
    report={"format":"frameforge-v2-pilot-render","version":1,"pilot":pilot,"project":str(project.relative_to(ROOT)),
            "video":str(video),"width":W,"height":H,"fps":fps,"frame_count":count,"duration_seconds":DURATION,
            "video_codec":"H.264","audio":audio_report,"audio_sha256":hashlib.sha256(audio.read_bytes()).hexdigest(),
            "voiceover":"Narration script included separately; no TTS voice is bundled.",
            "visuals":"Original procedural artwork only; no external footage, image-generation service or franchise character assets.",
            "size_mb":round(video.stat().st_size/(1024*1024),2)}
    (out/"render-report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot",choices=tuple(PILOTS),required=True)
    parser.add_argument("--output-dir",required=True)
    parser.add_argument("--fps",type=int,choices=(24,25,30),default=FPS)
    args=parser.parse_args(argv)
    try: print(json.dumps(render_pilot(args.pilot,args.output_dir,args.fps),indent=2))
    except Exception as exc: parser.exit(1,"ERROR: "+str(exc)+"\n")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
