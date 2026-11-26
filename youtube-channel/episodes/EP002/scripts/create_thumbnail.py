#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"output"
OUT.mkdir(exist_ok=True,parents=True)
W,H=1280,720
im=Image.new("RGB",(W,H),(6,15,31))
px=im.load()
for y in range(H):
 for x in range(W):
  t=x/W; glow=max(0,1-math.sqrt(((x-955)/560)**2+((y-330)/540)**2))
  px[x,y]=(int(5+11*t+14*glow),int(14+20*t+32*glow),int(31+28*t+48*glow))
d=ImageDraw.Draw(im,"RGBA")
for x in range(660,1280,60): d.line((x,0,x,720),fill=(70,115,165,24),width=1)
for y in range(20,720,60): d.line((640,y,1280,y),fill=(70,115,165,22),width=1)
d.rounded_rectangle((690,70,1225,545),radius=38,fill=(12,25,43,225),outline=(71,114,157,180),width=5)
d.rounded_rectangle((720,100,1195,515),radius=28,fill=(4,12,23,230),outline=(110,149,180,150),width=3)
d.rounded_rectangle((750,130,1165,180),radius=20,fill=(33,57,79,255),outline=(119,161,196,180),width=3)
d.rounded_rectangle((760,440,1155,490),radius=18,fill=(29,51,72,255),outline=(119,161,196,180),width=3)
d.polygon([(830,205),(1030,165),(1065,185),(860,228)],fill=(166,194,221,255),outline=(240,249,255,255))
d.polygon([(895,284),(1090,250),(1120,270),(925,306)],fill=(117,156,190,255),outline=(226,243,255,255))
d.line((780,235,1000,200,1080,270,1135,350),fill=(245,91,106,220),width=7)
d.ellipse((845,328,1115,414),fill=(25,67,110,255),outline=(188,222,255,240),width=5)
d.ellipse((870,340,1090,399),outline=(100,185,236,210),width=3)
for k in range(1,6): d.ellipse((865+k*7,338+k*3,1096-k*7,405-k*3),outline=(79,152,210,80),width=2)
for xx in range(890,1075,24): d.line((xx,348,xx,394),fill=(150,204,242,85),width=1)
for yy in range(355,394,10): d.line((875,yy,1085,yy),fill=(150,204,242,75),width=1)
d.rectangle((0,0,18,H),fill=(214,40,57,255)); d.rectangle((18,0,W,9),fill=(23,70,162,255))
font_b="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
font_r="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
d.rounded_rectangle((46,70,615,638),radius=24,fill=(5,14,29,168),outline=(75,112,153,100),width=2)
d.text((86,112),"UNDERNEATH EVERYTHING",font=ImageFont.truetype(font_b,19),fill=(159,193,223,255))
d.rectangle((86,154,174,162),fill=(214,40,57,255))
d.text((82,211),"THE CHIP-",font=ImageFont.truetype(font_b,57),fill=(255,255,255,255),stroke_width=1,stroke_fill=(5,12,25,255))
d.text((82,283),"MAKING",font=ImageFont.truetype(font_b,64),fill=(255,255,255,255),stroke_width=1,stroke_fill=(5,12,25,255))
d.text((82,360),"MACHINE",font=ImageFont.truetype(font_b,64),fill=(255,255,255,255),stroke_width=1,stroke_fill=(5,12,25,255))
d.text((86,462),"THE ENGINEERING BEHIND THE CHIP",font=ImageFont.truetype(font_r,17),fill=(180,210,235,255))
d.rounded_rectangle((1004,625,1234,683),radius=12,fill=(214,40,57,250),outline=(255,255,255,220),width=2)
f=ImageFont.truetype(font_b,20); bb=d.textbbox((0,0),"EDUCATIONAL",font=f)
d.text((1119-(bb[2]-bb[0])/2,643),"EDUCATIONAL",font=f,fill=(255,255,255,255))
d.rectangle((18,H-10,W,H),fill=(23,70,162,255))
im.save(OUT/"thumbnail_rwb.png",optimize=True)
print(OUT/"thumbnail_rwb.png")