
def build_city(center):
    floor("Vesper asphalt",center,0,38,22,MAT["asphalt"])
    cube("Vesper far skyline",(center,11,9),(38,0.8,18),MAT["building dark"],0.08)
    for i in range(8):
        x=center-16+i*4.5
        h=8+(i%3)*3
        cube("Vesper building "+str(i),(x,8,h/2),(3.8,3.0,h),MAT["building "+str(i%3)],0.06)
        for z in range(2,int(h)-1,2):
            for dx in (-1.1,0,1.1):
                cube("Lit window",(x+dx,6.47,z),(0.62,0.035,0.88),MAT["window glow" if (i+z)%3 else "window dark"],0.015)
    for lane in range(11):
        cube("Road centre stripe",(center-17+lane*3.4,0,0.012),(1.7,0.11,0.025),MAT["road paint"],0.01)
    for side in (-1,1):
        cube("Concrete pavement",(center,side*7,0.06),(38,3.0,0.18),MAT["sidewalk"],0.04)
        for i in range(6):
            x=center-15+i*6
            cylinder("Street lamp pole",(x,side*6.1,3.0),0.055,6.0,MAT["dark metal"])
            cube("Street lamp head",(x,side*6.1,6.0),(0.55,0.22,0.12),MAT["lamp glass"],0.035)
    # A believable compact sedan, with glazing, trim, lamps, tyres and wheel hubs.
    def car(name,x,y,scale=1.0,paint=None):
        paint=paint or MAT["car paint"]
        body=cube(name+" lower body",(x,y,0.72*scale),(2.2*scale,4.4*scale,0.68*scale),paint,0.22)
        cube(name+" bonnet",(x,y-1.42*scale,1.03*scale),(2.0*scale,1.45*scale,0.24*scale),paint,0.12)
        cube(name+" roof",(x,y+0.10*scale,1.56*scale),(1.75*scale,1.95*scale,0.56*scale),MAT["car glass frame"],0.20)
        cube(name+" windscreen",(x,y-0.91*scale,1.50*scale),(1.58*scale,0.06*scale,0.50*scale),MAT["car glass"],0.05)
        cube(name+" rear glass",(x,y+1.08*scale,1.50*scale),(1.58*scale,0.06*scale,0.48*scale),MAT["car glass"],0.04)
        for side in (-1,1):
            cube(name+" side glass "+str(side),(x+side*0.89*scale,y+0.12*scale,1.54*scale),(0.06*scale,1.70*scale,0.42*scale),MAT["car glass"],0.04)
            for wy in (-1.38,1.36):
                wheel=cylinder(name+" tyre",(x+side*1.08*scale,y+wy*scale,0.48*scale),0.42*scale,0.22*scale,MAT["rubber"],(math.pi/2,0,0),"BROWN • Vehicles")
                cylinder(name+" alloy hub",(x+side*1.205*scale,y+wy*scale,0.48*scale),0.22*scale,0.03*scale,MAT["alloy"],(math.pi/2,0,0),"BROWN • Vehicles")
            cube(name+" headlamp "+str(side),(x+side*0.72*scale,y-2.22*scale,0.84*scale),(0.32*scale,0.05*scale,0.20*scale),MAT["headlight"],0.035)
            cube(name+" tail lamp "+str(side),(x+side*0.72*scale,y+2.22*scale,0.84*scale),(0.32*scale,0.05*scale,0.20*scale),MAT["tail light"],0.035)
        cube(name+" front grille",(x,y-2.24*scale,0.60*scale),(0.85*scale,0.035*scale,0.22*scale),MAT["grille"],0.025)
        return body
    car("Vesper taxi",center-7,2,0.94,MAT["taxi paint"])
    car("Passing sedan",center+8,-3,0.88,MAT["car paint"])
    # Transit bus in the deep background, parked safely behind the crossing.
    cube("Public transit bus body",(center+1,9,1.75),(3.3,8.4,3.1),MAT["bus paint"],0.35,"BROWN • Vehicles")
    cube("Public transit bus windows",(center+1,4.7,2.1),(3.08,0.035,1.2),MAT["car glass"],0.08,"BROWN • Vehicles")
    for x in (center-0.2,center+1.0,center+2.2):
        cube("Bus side window",(x,8.5,2.12),(0.035,5.5,1.12),MAT["car glass"],0.03,"BROWN • Vehicles")
    for x in (center-0.15,center+1.0,center+2.15):
        cylinder("Bus wheel",(x,6.0,0.62),0.50,0.25,MAT["rubber"],(math.pi/2,0,0),"BROWN • Vehicles")
    cube("Public information display",(center-10,-6.0,3.2),(3.2,0.22,2.2),MAT["screen frame"],0.10)
    cube("Public information display glass",(center-10,-6.14,3.2),(2.92,0.035,1.92),MAT["screen glow"],0.02)
    text_obj("Public display label","VESPER  /  CITY SERVICES",(center-10,-6.18,3.35),0.20,MAT["sign white"])
    # Kaylen's route remains ordinary pedestrian movement through the city.
    kaylen=character("Kaylen Atlee — street",(center-1,-1.6,0),(0.37,0.20,0.15),(0.022,0.018,0.016),(0.09,0.14,0.19),(0.075,0.085,0.10),"fade",0.99)
    return kaylen

def build_room(center, phone_focus=False):
    floor("Interior floor",center,0,14,12,MAT["wood floor"])
    cube("Interior rear wall",(center,5,2.8),(14,0.32,5.6),MAT["interior plaster"],0.05)
    cube("Interior side wall",(center-7,0,2.8),(0.32,10,5.6),MAT["interior plaster"],0.05)
    cube("Large window frame",(center+3.2,4.78,3.1),(3.8,0.12,2.9),MAT["window frame"],0.05)
    cube("Window glass",(center+3.2,4.69,3.1),(3.48,0.025,2.58),MAT["window glass"],0.015)
    # Softly lit curtain panels and a practical hanging ceiling lamp.
    for x in (center+1.3,center+5.1):
        cube("Curtain panel",(x,4.54,3.05),(0.42,0.08,3.15),MAT["curtain"],0.05)
    cube("Interior table",(center,-0.3,0.82),(3.2,1.45,0.16),MAT["walnut"],0.07)
    for x in (center-1.35,center+1.35):
        for y in (-0.8,0.2):
            cylinder("Table leg",(x,y,0.38),0.055,0.82,MAT["dark metal"])
    cylinder("Coffee mug",(center-0.85,-0.3,1.02),0.15,0.29,MAT["ceramic"])
    torus("Mug handle",(center-1.02,-0.3,1.02),0.10,0.025,MAT["ceramic"],(math.pi/2,0,0))
    cube("Television cabinet",(center-4,3.4,1.1),(2.0,0.48,1.6),MAT["walnut"],0.08)
    cube("Television screen",(center-4,3.12,2.18),(1.9,0.06,1.12),MAT["screen frame"],0.05)
    cube("Television image",(center-4,3.075,2.18),(1.74,0.015,0.96),MAT["screen glow"],0.02)
    text_obj("Broadcast graphic","COMMUNITY  /  RESILIENCE",(center-4,3.05,2.2),0.105,MAT["sign white"])
    kaylen=character("Kaylen Atlee — interior",(center-0.45,-1.7,0),(0.37,0.20,0.15),(0.022,0.018,0.016),(0.09,0.14,0.19),(0.075,0.085,0.10),"fade",0.99)
    return kaylen

def build_alley(center):
    floor("Memory pavement",center,0,16,12,MAT["asphalt"])
    cube("Alley wall",(center,4,2.4),(16,0.3,4.8),MAT["brick"],0.08)
    for x in range(-7,8,2):
        cube("Alley brick course",(center+x,3.82,1.6),(1.7,0.04,0.08),MAT["brick mortar"],0.015)
    cylinder("Bottle body",(center-0.6,-0.8,0.16),0.10,0.44,MAT["green glass"],(math.pi/2,0,0))
    cylinder("Bottle neck",(center-0.6,-1.05,0.16),0.045,0.20,MAT["green glass"],(math.pi/2,0,0))
    for i in range(5):
        shard= cube("Glass fragment "+str(i),(center-1.0+i*0.22,-0.85+(i%2)*0.3,0.04),(0.12,0.22,0.018),MAT["glass shard"],0.01)
        shard.rotation_euler[2]=(i-2)*0.31
    for x in (-6,-2,2,6):
        cube("Alley service door",(center+x,3.75,1.35),(1.25,0.12,2.7),MAT["door"],0.035)
    kaylen=character("Kaylen Atlee — memory",(center+1.2,-2.4,0),(0.37,0.20,0.15),(0.022,0.018,0.016),(0.09,0.14,0.19),(0.075,0.085,0.10),"fade",0.99)
    return kaylen

def build_printshop(center, variant="wide"):
    floor("Print shop floor",center,0,18,13,MAT["concrete"])
    cube("Print shop rear wall",(center,5.9,2.7),(18,0.35,5.4),MAT["aged plaster"],0.07)
    cube("Print shop left wall",(center-8.8,0,2.7),(0.35,12,5.4),MAT["aged plaster"],0.07)
    cube("Print shop right wall",(center+8.8,0,2.7),(0.35,12,5.4),MAT["aged plaster"],0.07)
    cube("Black painted windows",(center-5.5,5.68,3.25),(4.2,0.05,2.2),MAT["window dark"],0.02)
    cube("Black painted windows 2",(center+5.5,5.68,3.25),(4.2,0.05,2.2),MAT["window dark"],0.02)
    text_obj("Grave Choir wall mark","GRAVE CHOIR  ♪",(center,5.65,4.2),0.62,MAT["chalk"])
    # Old print equipment and paper stacks make the room a former print shop.
    cube("Old printing press",(center-6.2,2.2,0.85),(2.1,1.8,1.6),MAT["press metal"],0.12)
    cylinder("Press roller",(center-6.2,1.1,1.05),0.28,1.6,MAT["dark metal"],(math.pi/2,0,0))
    for i in range(4):
        cube("Paper ream "+str(i),(center-5.8+i*0.24,1.1,0.25),(0.72,0.9,0.15),MAT["paper"],0.015)
    cube("Crew meeting table",(center,0.8,0.78),(6.6,2.1,0.14),MAT["walnut"],0.06)
    for x in (-2.9,2.9):
        for y in (0.0,1.5):
            cylinder("Meeting table leg",(center+x,y,0.38),0.055,0.77,MAT["dark metal"])
    # Screens and work station.
    for x in (center+3.6,center+4.8):
        cube("Computer monitor body",(x,3.55,1.85),(1.1,0.15,0.9),MAT["screen frame"],0.035)
        cube("Computer monitor display",(x,3.455,1.85),(0.97,0.025,0.75),MAT["screen glow"],0.015)
        cube("Monitor stand",(x,3.58,1.29),(0.15,0.16,0.28),MAT["dark metal"],0.02)
    # Instant noodles, kettle and mending table props.
    for x in (-1.8,-1.1):
        cylinder("Noodle cup",(center+x,0.1,0.96),0.16,0.28,MAT["paper"])
        torus("Cup rim",(center+x,0.1,1.10),0.15,0.012,MAT["brass"])
    kettle= cylinder("Kettle body",(center+2.2,0.1,1.12),0.23,0.47,MAT["kettle metal"])
    torus("Kettle handle",(center+2.2,0.1,1.42),0.18,0.035,MAT["dark metal"],(math.pi/2,0,0))
    cylinder("Kettle lid",(center+2.2,0.1,1.38),0.13,0.055,MAT["brass"])
    # School application and writing pen.
    cube("School application",(center-0.55,-0.02,0.97),(0.72,0.96,0.018),MAT["paper"],0.006)
    for i in range(6):
        cube("Application text line "+str(i),(center-0.55,-0.35+i*0.12,0.984),(0.48-(i%2)*0.10,0.008,0.006),MAT["ink"],0.002)
    cylinder("Pen",(center-0.05,-0.05,1.04),0.018,0.66,MAT["pen"],(math.pi/2,0,0))
    # Medical pouch.
    pouch=cube("Medical pouch",(center+0.8,-0.1,1.02),(0.46,0.28,0.22),MAT["medical pouch"],0.06)
    cube("Pouch cross",(center+0.8,-0.252,1.02),(0.08,0.018,0.15),MAT["sign white"],0.01)
    cube("Pouch cross bar",(center+0.8,-0.255,1.02),(0.18,0.018,0.06),MAT["sign white"],0.01)
    # Seats and practical hanging bulbs.
    for x in (-4.2,-2.0,2.0,4.2):
        cube("Print shop chair seat",(center+x,-1.1,0.55),(0.8,0.75,0.12),MAT["chair"],0.06)
        cube("Print shop chair back",(center+x,-1.43,1.0),(0.8,0.12,0.85),MAT["chair"],0.06)
    for x in (-5,0,5):
        cylinder("Pendant cord",(center+x,0,4.45),0.014,1.2,MAT["dark metal"])
        uv("Pendant shade",(center+x,0,3.8),(0.35,0.35,0.16),MAT["brass"],group="BROWN • Lighting")
        point_light("Warm printshop pendant",(center+x,0,3.75),110,(1.0,0.66,0.36),0.55)
    return

def build_materials():
    material("limestone",(0.46,0.43,0.36),0.84,0,0,85,0.08)
    material("marble",(0.59,0.57,0.50),0.34,0,0,120,0.045)
    material("brass",(0.42,0.27,0.10),0.28,0.78)
    material("dark metal",(0.035,0.045,0.052),0.33,0.75,0,115,0.08)
    material("registry floor",(0.12,0.14,0.16),0.31,0.12,0,130,0.06)
    material("ceiling",(0.17,0.18,0.19),0.82,0)
    material("walnut",(0.16,0.085,0.045),0.38,0,0,75,0.10)
    material("stone top",(0.32,0.33,0.31),0.28,0.08)
    material("screen frame",(0.012,0.018,0.023),0.25,0.48)
    emissive("screen glow",(0.035,0.19,0.24),1.3)
    material("paper",(0.76,0.72,0.61),0.89,0,0,175,0.035)
    material("ink",(0.025,0.03,0.04),0.6)
    material("sign gold",(0.68,0.49,0.22),0.32,0.4)
    material("sign white",(0.78,0.76,0.69),0.35)
    material("corridor floor",(0.24,0.24,0.22),0.55,0,0,95,0.05)
    material("pale plaster",(0.52,0.49,0.42),0.82,0,0,90,0.08)
    material("door",(0.10,0.14,0.16),0.45,0.12,0,110,0.04)
    material("door inset",(0.16,0.19,0.20),0.52,0.08)
    material("window glass",(0.045,0.11,0.14),0.13,0.28)
    material("window frame",(0.08,0.09,0.095),0.4,0.65)
    emissive("light panel",(0.66,0.68,0.63),2.0)
    material("asphalt",(0.045,0.052,0.058),0.94,0,0,150,0.12)
    material("building dark",(0.04,0.06,0.08),0.65,0.22,0,70,0.09)
    material("building 0",(0.12,0.14,0.16),0.72,0.16)
    material("building 1",(0.19,0.16,0.14),0.72,0.10)
    material("building 2",(0.12,0.15,0.17),0.70,0.14)
    emissive("window glow",(0.48,0.36,0.18),1.4)
    material("window dark",(0.012,0.024,0.035),0.24,0.2)
    material("road paint",(0.72,0.62,0.42),0.72)
    material("sidewalk",(0.22,0.23,0.22),0.82,0,0,110,0.05)
    emissive("lamp glass",(0.75,0.47,0.22),2.0)
    material("car paint",(0.11,0.17,0.22),0.24,0.48,0,90,0.04)
    material("taxi paint",(0.63,0.44,0.12),0.28,0.33,0,85,0.04)
    material("car glass",(0.018,0.045,0.06),0.12,0.42)
    material("car glass frame",(0.025,0.033,0.039),0.28,0.6)
    material("alloy",(0.42,0.45,0.48),0.22,0.85)
    material("rubber",(0.012,0.014,0.016),0.88,0)
    emissive("headlight",(0.78,0.68,0.47),2.8)
    material("tail light",(0.38,0.025,0.018),0.25,0.1)
    material("grille",(0.025,0.03,0.035),0.38,0.7)
    material("bus paint",(0.10,0.24,0.28),0.32,0.28)
    material("wood floor",(0.16,0.11,0.075),0.62,0,0,100,0.06)
    material("interior plaster",(0.34,0.32,0.27),0.82,0,0,90,0.06)
    material("curtain",(0.18,0.17,0.15),0.9,0,0,180,0.1)
    material("ceramic",(0.40,0.36,0.30),0.22,0)
    material("brick",(0.15,0.10,0.08),0.87,0,0,65,0.12)
    material("brick mortar",(0.20,0.17,0.14),0.94)
    material("green glass",(0.025,0.18,0.10),0.08,0.2)
    material("glass shard",(0.28,0.42,0.39),0.11,0.35)
    material("aged plaster",(0.26,0.24,0.20),0.93,0,0,55,0.14)
    material("press metal",(0.045,0.06,0.068),0.38,0.72,0,90,0.09)
    material("kettle metal",(0.30,0.32,0.33),0.24,0.82)
    material("pen",(0.035,0.065,0.09),0.3,0.42)
    material("medical pouch",(0.17,0.21,0.17),0.92,0,0,160,0.08)
    material("chair",(0.07,0.09,0.10),0.62,0.12)
    material("chalk",(0.78,0.75,0.66),0.95,0)

def build_scene(output_dir):
    # Reset the default scene and all data for deterministic, repeatable builds.
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for c in list(bpy.data.collections):
        if c.name in bpy.context.scene.collection.children:
            bpy.context.scene.collection.children.unlink(c)
        bpy.data.collections.remove(c)
    MAT.clear()
    COL.clear()
    build_materials()
    scene=bpy.context.scene
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=20
    scene.cycles.use_denoising=True
    scene.render.resolution_x=W
    scene.render.resolution_y=H
    scene.render.resolution_percentage=100
    scene.render.fps=FPS
    scene.frame_start=1
    scene.frame_end=TOTAL_FRAMES
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGB"
    scene.render.film_transparent=False
    scene.render.use_motion_blur=True
    scene.render.motion_blur_shutter=0.35
    try:
        scene.view_settings.view_transform="AgX"
    except Exception:
        scene.view_settings.view_transform="Filmic"
    scene.world.color=(0.025,0.03,0.04)
    if scene.world.use_nodes:
        bg=scene.world.node_tree.nodes.get("Background")
        bg.inputs["Color"].default_value=(0.055,0.068,0.085,1)
        bg.inputs["Strength"].default_value=0.35
    scene.render.image_settings.color_depth="8"
    scene.cycles.preview_samples=12
    # Registry and source-related set builds.
    clerk=build_registry(0)
    build_corridor(80)
    build_turnstile(120)
    kaylen_street=build_city(160)
    kaylen_room=build_room(200)
    kaylen_memory=build_alley(240)
    kaylen_phone=build_room(280,True)
    # Printshop exterior and three matching interior set stages.
    floor("Print shop exterior ground",320,0,16,10,MAT["asphalt"])
    cube("Print shop facade",(320,4,2.5),(12,0.5,5),MAT["aged plaster"],0.08)
    cube("Print shop door",(320,-? if False else 3.72,1.55),(2.1,0.13,3.1),MAT["door"],0.04)
    cube("Black window left",(316.7,3.70,2.6),(3.0,0.08,2.0),MAT["window dark"],0.02)
    cube("Black window right",(323.3,3.70,2.6),(3.0,0.08,2.0),MAT["window dark"],0.02)
    text_obj("Print shop facade name","OLD CITY PRINT WORKS",(320,3.62,4.1),0.25,MAT["sign gold"])
    for c in (360,400,440):
        build_printshop(c)
    # A single character can be read in profile and full group continuity is maintained.
    clerk.location=(0,-2.6,0)
    kaylen_print=character("Kaylen Atlee — printshop approach",(320,-2.0,0),(0.37,0.20,0.15),(0.022,0.018,0.016),(0.09,0.14,0.19),(0.075,0.085,0.10),"fade",0.99)
    # Group scene: each character remains an individual model with independent performance keys.
    crew_specs=[
        ("Kaylen Atlee — crew",(360-2.2,-0.4,0),(0.37,0.20,0.15),(0.022,0.018,0.016),(0.09,0.14,0.19),(0.075,0.085,0.10),"fade"),
        ("Kesh Ayo",(360-5.7,0.6,0),(0.34,0.19,0.14),(0.03,0.022,0.018),(0.14,0.18,0.16),(0.08,0.09,0.10),"short"),
        ("Amel Zori",(360+5.3,0.6,0),(0.43,0.25,0.18),(0.035,0.03,0.04),(0.19,0.12,0.20),(0.11,0.10,0.12),"bun"),
        ("Juno Saye",(360-1.1,1.7,0),(0.39,0.23,0.17),(0.025,0.02,0.018),(0.13,0.17,0.17),(0.10,0.10,0.10),"locs"),
        ("Biko Nare",(360+2.1,-0.2,0),(0.48,0.29,0.20),(0.07,0.04,0.025),(0.38,0.25,0.13),(0.14,0.13,0.12),"curls"),
        ("Tovin Bell",(360-3.7,1.0,0),(0.39,0.20,0.14),(0.025,0.03,0.04),(0.40,0.25,0.12),(0.13,0.19,0.28),"short",0.96),
        ("Lark Temba",(360+4.1,1.3,0),(0.33,0.19,0.14),(0.035,0.03,0.03),(0.15,0.15,0.19),(0.12,0.13,0.16),"locs"),
        ("Rasha Deni",(360-5.0,-1.1,0),(0.41,0.24,0.18),(0.025,0.02,0.018),(0.30,0.13,0.15),(0.11,0.10,0.11),"bun"),
        ("Sefu Malk",(360+5.8,-1.1,0),(0.35,0.20,0.15),(0.035,0.03,0.025),(0.16,0.17,0.14),(0.09,0.10,0.10),"short"),
    ]
    crew={}
    for spec in crew_specs:
        nm,pos,sk,ha,jk,tr,hs,*rest=spec
        ht=rest[0] if rest else 1.0
        crew[nm]=character(nm,pos,sk,ha,jk,tr,hs,ht)
    eamon_wide=character("Eamon Voss",(440+0.2,3.0,0),(0.42,0.25,0.18),(0.018,0.016,0.014),(0.035,0.045,0.06),(0.07,0.08,0.09),"short",1.02)
    lark_wide=character("Lark Temba — doorway",(440+4.5,2.5,0),(0.33,0.19,0.14),(0.035,0.03,0.03),(0.15,0.15,0.19),(0.12,0.13,0.16),"locs")
    biko_close=character("Biko Nare — doorway",(440-3.0,0.0,0),(0.48,0.29,0.20),(0.07,0.04,0.025),(0.38,0.25,0.13),(0.14,0.13,0.12),"curls")
    amel_close=character("Amel Zori — doorway",(440-0.2,0.0,0),(0.43,0.25,0.18),(0.035,0.03,0.04),(0.19,0.12,0.20),(0.11,0.10,0.12),"bun")
    kaylen_treatment=character("Kaylen Atlee — care",(400-1.1,-0.4,0),(0.37,0.20,0.15),(0.022,0.018,0.016),(0.09,0.14,0.19),(0.075,0.085,0.10),"fade",0.99)
    juno_treatment=character("Juno Saye — care",(400+0.65,-0.2,0),(0.39,0.23,0.17),(0.025,0.02,0.018),(0.13,0.17,0.17),(0.10,0.10,0.10),"locs")
    # Character positions are fixed by the shot; animate Kaylen's walk into Vesper.
    animate_root(kaylen_street,[FPS*100+1,FPS*125],[(159,-1.6,0),(161.4,-1.6,0)])
    animate_root(kaylen_print,[FPS*200+1,FPS*225],[(318,-2.0,0),(320,-2.0,0)])
    # Small, motivated movements, not looping idle cycles.
    for root, f, zrot in ((clerk,FPS*0+1,0.0),(crew["Juno Saye"],FPS*250+1,0.03),(eamon_wide,FPS*275+1,-0.04)):
        root.rotation_euler[2]=zrot
        root.keyframe_insert(data_path="rotation_euler",frame=f)
    # Lighting is designed per environment with warm practicals and cool ambient fills.
    for c, p in ((0,1500),(40,900),(80,1300),(120,1100),(160,1900),(200,850),(240,1000),(280,900),(320,950),(360,900),(400,900),(440,1100)):
        light_set(c,power=p)
    # Add practical lighting to city screens and print-shop details.
    point_light("Street display glow",(150,-6,3),170,(0.25,0.55,0.75),1.8)
    point_light("Print press work light",(354,-1,3.1),120,(1.0,0.55,0.28),0.8)
    # Each 25-second sequence has its own motivated framing, lens and subtle dolly.
    shots=[
      (0,0,(0,-15,7.2),(0,0,2.2),38,(0,1.2,-0.4)),
      (1,40,(38.2,-4.2,2.0),(40,0,1.05),78,(0.55,0.05,0)),
      (2,80,(80,-14,2.8),(80,2.0,2.2),42,(0,2.5,0)),
      (3,120,(120,-7,2.3),(120,0,1.0),58,(0.2,0.2,0)),
      (4,160,(160,-22,7.5),(160,1.0,2.0),30,(2.4,1.8,-0.6)),
      (5,200,(198,-7,2.6),(200,-0.2,1.45),55,(0.3,0.7,0)),
      (6,240,(239,-5,1.1),(239,-0.8,0.12),84,(0.4,0.35,0)),
      (7,280,(280,-4.5,1.6),(280,-0.3,1.0),80,(0.25,0.1,0)),
      (8,320,(320,-12,3.0),(320,2.8,2.1),45,(0.4,1.0,0)),
      (9,360,(360,-15,5.0),(360,0.6,1.6),38,(0.45,1.1,-0.15)),
      (10,400,(397.5,-6.2,2.35),(400,-0.1,1.65),72,(0.25,0.2,0)),
      (11,440,(440,-13,3.0),(440,1.2,1.7),45,(0.2,0.9,-0.1)),
    ]
    scene.camera=None
    for idx,center,loc,target,lens,travel in shots:
        start=idx*SHOT_SECONDS*FPS+1
        end=(idx+1)*SHOT_SECONDS*FPS
        add_camera_shot("PILOT CAMERA "+str(idx+1),start,end,loc,target,lens,travel)
    # Set opening camera and named frame markers for editorial review.
    scene.camera=bpy.data.objects.get("PILOT CAMERA 1")
    for idx in range(12):
        frame=idx*SHOT_SECONDS*FPS+1
        scene.timeline_markers.new("SHOT "+str(idx+1).zfill(2)+" / "+str(idx*25).zfill(3)+"s",frame=frame)
    # Small focal-depth defaults; the camera objects carry their own DoF data.
    scene.render.filepath=str(output_dir/"frames"/"frame_")
    scene["project"]="BROWN Book One — five-minute visual pilot"
    scene["status"]="DRAFT PILOT RENDER — author review required"
    scene["frame_count"]=TOTAL_FRAMES
    scene["fps"]=FPS
    scene["resolution"]="1280x720"
    scene["render_engine"]="Cycles CPU with denoising"
    scene["style"]="Realistic 3D materials and human-scale forms; provisional models, not approved likenesses."
    for c in bpy.data.collections:
        c.hide_select=False
    output_dir.mkdir(parents=True,exist_ok=True)
    blend_path=output_dir/"BROWN_Five_Minute_Pilot.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    # A first-frame lighting and asset check is included in the build artifact.
    still_dir=output_dir/"build_still"
    still_dir.mkdir(parents=True,exist_ok=True)
    scene.frame_set(1)
    scene.render.filepath=str(still_dir/"pilot_frame_000001.png")
    scene.render.image_settings.file_format="PNG"
    bpy.ops.render.render(write_still=True)
    report={
      "status":"BUILT_NOT_VISUALLY_APPROVED",
      "runtime_seconds":TOTAL_SECONDS,"frames":TOTAL_FRAMES,
      "fps":FPS,"resolution":[W,H],"engine":"CYCLES_CPU","samples":scene.cycles.samples,
      "objects":len(bpy.data.objects),"characters":"11 source-referenced hero/background models; appearance draft only",
      "sets":["registry hall","registry desk","service corridor","turnstile","Vesper street","unspecified interior","memory pavement","print shop exterior","print shop interior"],
      "vehicle_assets":["taxi sedan","sedan","public transit bus"],
      "blend_file":str(blend_path)
    }
    (output_dir/"pilot_build_report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    return blend_path

def render_segment(output_dir, segment):
    if segment<1 or segment>5:
        raise ValueError("Pilot segment must be between 1 and 5")
    scene=bpy.context.scene
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=20
    scene.cycles.use_denoising=True
    scene.render.resolution_x=W
    scene.render.resolution_y=H
    scene.render.resolution_percentage=100
    scene.render.fps=FPS
    start=(segment-1)*SEGMENT_SECONDS*FPS+1
    end=segment*SEGMENT_SECONDS*FPS
    scene.frame_start=start
    scene.frame_end=end
    frames=output_dir/"frames"
    frames.mkdir(parents=True,exist_ok=True)
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGB"
    scene.render.filepath=str(frames/"frame_")
    scene.render.use_file_extension=True
    scene.render.image_settings.color_depth="8"
    scene.render.threads_mode="FIXED"
    scene.render.threads=2
    scene.frame_set(start)
    print("Rendering frames",start,"to",end,"at",W,"x",H,"24 fps")
    bpy.ops.render.render(animation=True)
    print("Completed segment",segment)

def main():
    a=args_parse()
    out=Path(a.output_dir).resolve()
    out.mkdir(parents=True,exist_ok=True)
    if a.mode=="build":
        build_scene(out)
        return
    if a.mode=="render":
        render_segment(out,a.segment)
        return

if __name__=="__main__":
    main()
