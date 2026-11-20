extends Control
## BLACKTIDE offline front end. No network, login, telemetry or remote service.

const CHARACTER_IDS := ["Aster","Bront","Koro","Luma","Miri","Nyx","Orin","Pika","Sola","Vey"]
const CHARACTER_ROLES := {
 "Aster":"BREACH / SCOUT", "Bront":"HEAVY / DEFENDER", "Koro":"RECON / MARKSMAN",
 "Luma":"SUPPORT / FIELD TECH", "Miri":"MEDIC / MOBILITY", "Nyx":"STEALTH / FLANKER",
 "Orin":"TACTICAL / CONTROL", "Pika":"RUNNER / ASSAULT", "Sola":"AERIAL / RECON",
 "Vey":"ENGINEER / HEAVY"
}
const WEAPON_NAMES := ["VESPER-9","FLUX SMG","AEGIS AR","KESTREL BURST","RANGER DMR",
 "LONGBOW","BREACH-12","BASTION LMG","PULSE CARBINE","ARC LANCE"]
const WEAPON_ROLES := ["SIDEARM","CLOSE QUARTERS","ALL-ROUND","BURST FIRE","PRECISION",
 "LONG RANGE","SHOTGUN","SUPPORT","ENERGY","CHARGED RAIL"]
const PROFILE_PATH := "user://blacktide_profile.cfg"
const SETTINGS_PATH := "user://blacktide_pvp.cfg"

var selected_character := "Aster"
var selected_weapon := 2
var current_page := "MAIN"
var page_root: Control
var preview_container: SubViewportContainer
var preview_viewport: SubViewport
var preview_stage: Node3D
var preview_model: Node3D
var preview_name: Label
var preview_role: Label
var status_line: Label

func _ready() -> void:
 set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
 _load_profile()
 _build_shell()
 _show_main()

func _process(_delta: float) -> void:
 if is_instance_valid(preview_model):
  preview_model.rotation.y = PI + sin(float(Time.get_ticks_msec()) * 0.00032) * 0.10

func _load_profile() -> void:
 var cfg := ConfigFile.new()
 if cfg.load(PROFILE_PATH) == OK:
  var candidate := str(cfg.get_value("profile","operator","Aster"))
  if candidate in CHARACTER_IDS:
   selected_character = candidate
  selected_weapon = clampi(int(cfg.get_value("profile","weapon",2)),0,WEAPON_NAMES.size()-1)

func _save_profile() -> void:
 var cfg := ConfigFile.new()
 cfg.load(PROFILE_PATH)
 cfg.set_value("profile","operator",selected_character)
 cfg.set_value("profile","weapon",selected_weapon)
 cfg.save(PROFILE_PATH)

func _build_shell() -> void:
 var bg := ColorRect.new()
 bg.color = Color(0.012,0.023,0.034,1.0)
 bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
 bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
 add_child(bg)
 var accent := ColorRect.new()
 accent.color = Color(0.06,0.68,0.70,0.85)
 accent.position = Vector2(64,48)
 accent.size = Vector2(5,72)
 add_child(accent)
 var logo := _label(self,"BLACKTIDE",Vector2(86,45),Vector2(490,65),48,Color(0.91,0.97,0.96),true)
 logo.add_theme_color_override("font_shadow_color",Color(0,0,0,0.6))
 _label(self,"GAMEFORGE  /  OFFLINE COMBAT OPERATIONS",Vector2(90,113),Vector2(520,25),15,Color(0.30,0.82,0.81),true)
 _label(self,"LOCAL MATCHES  •  NO ACCOUNT  •  NO INTERNET REQUIRED",Vector2(90,142),Vector2(540,22),11,Color(0.48,0.62,0.66))
 _build_preview()
 page_root = Control.new()
 page_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
 add_child(page_root)
 status_line = _label(self,"OFFLINE SYSTEMS READY",Vector2(70,682),Vector2(650,20),11,Color(0.38,0.75,0.73))
 _label(self,"BUILD 0.3  /  BLACKTIDE PORT",Vector2(950,682),Vector2(270,20),11,Color(0.36,0.52,0.57),false,HORIZONTAL_ALIGNMENT_RIGHT)

func _build_preview() -> void:
 var frame := PanelContainer.new()
 frame.position = Vector2(650,44)
 frame.size = Vector2(570,620)
 var style := StyleBoxFlat.new()
 style.bg_color = Color(0.025,0.046,0.061,0.92)
 style.border_color = Color(0.13,0.42,0.46,0.85)
 style.set_border_width_all(1)
 style.corner_radius_top_left = 14
 style.corner_radius_top_right = 14
 style.corner_radius_bottom_left = 14
 style.corner_radius_bottom_right = 14
 frame.add_theme_stylebox_override("panel",style)
 add_child(frame)
 preview_container = SubViewportContainer.new()
 preview_container.position = Vector2(6,6)
 preview_container.size = Vector2(558,555)
 preview_container.stretch = true
 frame.add_child(preview_container)
 preview_viewport = SubViewport.new()
 preview_viewport.size = Vector2i(558,555)
 preview_viewport.own_world_3d = true
 preview_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
 preview_container.add_child(preview_viewport)
 preview_stage = Node3D.new()
 preview_viewport.add_child(preview_stage)
 var env_node := WorldEnvironment.new()
 var env := Environment.new()
 env.background_mode = Environment.BG_COLOR
 env.background_color = Color(0.025,0.049,0.068)
 env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
 env.ambient_light_color = Color(0.48,0.59,0.63)
 env.ambient_light_energy = 0.72
 env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
 env_node.environment = env
 preview_stage.add_child(env_node)
 var floor := MeshInstance3D.new()
 var plane := PlaneMesh.new()
 plane.size = Vector2(14,14)
 floor.mesh = plane
 floor.position.y = -0.04
 var floor_mat := StandardMaterial3D.new()
 floor_mat.albedo_color = Color(0.035,0.065,0.078)
 floor_mat.metallic = 0.28
 floor_mat.roughness = 0.48
 floor.material_override = floor_mat
 preview_stage.add_child(floor)
 var light := DirectionalLight3D.new()
 light.rotation_degrees = Vector3(-34,-28,0)
 light.light_energy = 1.35
 light.shadow_enabled = true
 preview_stage.add_child(light)
 var rim := OmniLight3D.new()
 rim.position = Vector3(-2.6,2.5,-2.0)
 rim.light_color = Color(0.12,0.82,0.88)
 rim.light_energy = 1.8
 rim.omni_range = 8.0
 preview_stage.add_child(rim)
 var camera := Camera3D.new()
 camera.position = Vector3(0,1.30,4.65)
 camera.fov = 38
 camera.look_at(Vector3(0,0.98,0),Vector3.UP)
 preview_stage.add_child(camera)
 camera.current = true
 preview_name = _label(frame,"ASTER",Vector2(22,566),Vector2(330,28),20,Color(0.92,0.97,0.95),true)
 preview_role = _label(frame,"BREACH / SCOUT",Vector2(22,594),Vector2(330,22),12,Color(0.24,0.78,0.78))
 _refresh_preview()

func _refresh_preview() -> void:
 if not is_instance_valid(preview_stage):
  return
 if is_instance_valid(preview_model):
  preview_model.queue_free()
  preview_model = null
 var path := "res://assets/characters/%s.glb" % selected_character
 if ResourceLoader.exists(path):
  var packed := load(path) as PackedScene
  if packed:
   preview_model = packed.instantiate() as Node3D
   preview_model.scale = Vector3.ONE * 0.88
   preview_model.rotation.y = PI
   preview_stage.add_child(preview_model)
   for child in preview_model.find_children("*","AnimationPlayer",true,false):
    var player := child as AnimationPlayer
    for clip in player.get_animation_list():
     if "idle" in clip.to_lower():
      player.play(clip)
      break
 if is_instance_valid(preview_name):
  preview_name.text = selected_character.to_upper()
 if is_instance_valid(preview_role):
  preview_role.text = CHARACTER_ROLES.get(selected_character,"TACTICAL OPERATOR")

func _clear_page() -> void:
 if is_instance_valid(page_root):
  for child in page_root.get_children():
   child.queue_free()

func _show_main() -> void:
 current_page = "MAIN"
 _clear_page()
 _panel(page_root,Vector2(66,190),Vector2(520,454))
 _label(page_root,"SELECT YOUR OPERATION",Vector2(92,208),Vector2(460,32),21,Color(0.88,0.95,0.93),true)
 _label(page_root,"A self-contained combat simulation. The match, bot, weapons and settings all run locally.",Vector2(92,245),Vector2(455,42),13,Color(0.53,0.68,0.70))
 _button(page_root,"DEPLOY  /  OFFLINE DUEL",Vector2(92,310),Vector2(455,62),_start_match,true)
 _button(page_root,"CHOOSE OPERATOR",Vector2(92,388),Vector2(455,54),_show_operators)
 _button(page_root,"ARMOURY  /  LOADOUT",Vector2(92,454),Vector2(455,54),_show_armoury)
 _button(page_root,"SETTINGS",Vector2(92,520),Vector2(218,50),_show_settings)
 _button(page_root,"QUIT",Vector2(329,520),Vector2(218,50),_quit_game)
 _label(page_root,"CURRENT OPERATOR  •  %s" % selected_character.to_upper(),Vector2(92,596),Vector2(460,20),12,Color(0.26,0.80,0.78),true)
 _label(page_root,"CURRENT WEAPON  •  %s" % WEAPON_NAMES[selected_weapon],Vector2(92,620),Vector2(460,20),12,Color(0.60,0.75,0.76))
 _set_status("READY TO DEPLOY  /  OFFLINE AI MATCH")

func _show_operators() -> void:
 current_page = "OPERATORS"
 _clear_page()
 _panel(page_root,Vector2(66,190),Vector2(520,454))
 _label(page_root,"OPERATOR SELECT",Vector2(92,208),Vector2(460,30),22,Color(0.90,0.97,0.95),true)
 _label(page_root,"Ten original rigged characters. Select your field operator.",Vector2(92,244),Vector2(460,24),12,Color(0.55,0.69,0.71))
 var grid := GridContainer.new()
 grid.position = Vector2(92,286)
 grid.size = Vector2(466,270)
 grid.columns = 2
 grid.add_theme_constant_override("h_separation",10)
 grid.add_theme_constant_override("v_separation",9)
 page_root.add_child(grid)
 for ident in CHARACTER_IDS:
  var b := Button.new()
  b.text = ident.to_upper() + ("  •  SELECTED" if ident==selected_character else "")
  b.custom_minimum_size = Vector2(225,47)
  _style_button(b,ident==selected_character)
  b.pressed.connect(func():
   selected_character=ident
   _refresh_preview()
   _show_operators()
   _set_status("OPERATOR EQUIPPED  /  "+ident.to_upper())
  )
  grid.add_child(b)
 _label(page_root,CHARACTER_ROLES.get(selected_character,""),Vector2(92,574),Vector2(450,22),13,Color(0.25,0.80,0.79),true)
 _button(page_root,"BACK",Vector2(92,606),Vector2(130,38),_show_main)

func _show_armoury() -> void:
 current_page = "ARMOURY"
 _clear_page()
 _panel(page_root,Vector2(66,190),Vector2(520,454))
 _label(page_root,"FIELD ARMOURY",Vector2(92,208),Vector2(460,30),22,Color(0.90,0.97,0.95),true)
 _label(page_root,"Choose one primary weapon for your next offline match.",Vector2(92,244),Vector2(460,24),12,Color(0.55,0.69,0.71))
 var grid := GridContainer.new()
 grid.position = Vector2(92,286)
 grid.size = Vector2(466,270)
 grid.columns = 2
 grid.add_theme_constant_override("h_separation",10)
 grid.add_theme_constant_override("v_separation",9)
 page_root.add_child(grid)
 for index in range(WEAPON_NAMES.size()):
  var b := Button.new()
  b.text = WEAPON_NAMES[index] + ("  •" if selected_weapon==index else "")
  b.custom_minimum_size = Vector2(225,47)
  _style_button(b,selected_weapon==index)
  b.pressed.connect(func():
   selected_weapon=index
   _show_armoury()
   _set_status("LOADOUT UPDATED  /  "+WEAPON_NAMES[index])
  )
  grid.add_child(b)
 _label(page_root,"EQUIPPED  •  %s  /  %s" % [WEAPON_NAMES[selected_weapon],WEAPON_ROLES[selected_weapon]],
  Vector2(92,574),Vector2(450,22),12,Color(0.25,0.80,0.79),true)
 _button(page_root,"BACK",Vector2(92,606),Vector2(130,38),_show_main)

func _show_settings() -> void:
 current_page = "SETTINGS"
 _clear_page()
 _panel(page_root,Vector2(66,190),Vector2(520,454))
 _label(page_root,"SYSTEM SETTINGS",Vector2(92,208),Vector2(460,30),22,Color(0.90,0.97,0.95),true)
 var cfg := ConfigFile.new()
 cfg.load(SETTINGS_PATH)
 var sensitivity := float(cfg.get_value("controls","look_sensitivity",1.0))
 var volume := float(cfg.get_value("audio","master_volume",0.82))
 var invert := bool(cfg.get_value("controls","invert_look_y",false))
 var assist := bool(cfg.get_value("controls","aim_assist",true))
 var quality_name := str(cfg.get_value("video","quality","BALANCED"))
 var sens_label := _label(page_root,"LOOK SENSITIVITY  •  %.2fx" % sensitivity,Vector2(92,258),Vector2(450,24),13,Color(0.77,0.88,0.87),true)
 var sens := HSlider.new()
 sens.position=Vector2(92,286);sens.size=Vector2(450,28);sens.min_value=.45;sens.max_value=2.4;sens.step=.05;sens.value=sensitivity
 page_root.add_child(sens)
 sens.value_changed.connect(func(v:float):
  sens_label.text="LOOK SENSITIVITY  •  %.2fx" % v
  cfg.set_value("controls","look_sensitivity",v);cfg.save(SETTINGS_PATH)
 )
 var vol_label := _label(page_root,"MASTER VOLUME  •  %d%%" % int(volume*100),Vector2(92,326),Vector2(450,24),13,Color(0.77,0.88,0.87),true)
 var vol := HSlider.new()
 vol.position=Vector2(92,354);vol.size=Vector2(450,28);vol.min_value=0.0;vol.max_value=1.0;vol.step=.01;vol.value=volume
 page_root.add_child(vol)
 vol.value_changed.connect(func(v:float):
  vol_label.text="MASTER VOLUME  •  %d%%" % int(v*100)
  cfg.set_value("audio","master_volume",v);cfg.save(SETTINGS_PATH)
  var bus:=AudioServer.get_bus_index("Master")
  if bus>=0:AudioServer.set_bus_volume_db(bus,linear_to_db(maxf(.001,v)))
 )
 var invert_box := CheckBox.new()
 invert_box.text="INVERT VERTICAL LOOK"
 invert_box.position=Vector2(92,398);invert_box.button_pressed=invert
 page_root.add_child(invert_box)
 invert_box.toggled.connect(func(v:bool):
  cfg.set_value("controls","invert_look_y",v);cfg.save(SETTINGS_PATH)
 )
 var assist_box := CheckBox.new()
 assist_box.text="SOFT AIM ASSIST"
 assist_box.position=Vector2(310,398);assist_box.button_pressed=assist
 page_root.add_child(assist_box)
 assist_box.toggled.connect(func(v:bool):
  cfg.set_value("controls","aim_assist",v);cfg.save(SETTINGS_PATH)
 )
 _label(page_root,"GRAPHICS PROFILE",Vector2(92,444),Vector2(180,26),13,Color(0.77,0.88,0.87),true)
 var quality := OptionButton.new()
 quality.position=Vector2(92,472);quality.size=Vector2(450,36)
 quality.add_item("LOW  /  30 FPS")
 quality.add_item("BALANCED  /  45 FPS")
 quality.add_item("HIGH  /  60 FPS")
 quality.select(0 if quality_name=="LOW" else (2 if quality_name=="HIGH" else 1))
 page_root.add_child(quality)
 quality.item_selected.connect(func(index:int):
  var names=["LOW","BALANCED","HIGH"]
  var fps=[30,45,60]
  cfg.set_value("video","quality",names[index])
  cfg.set_value("video","fps",fps[index])
  cfg.save(SETTINGS_PATH)
 )
 _label(page_root,"All settings are saved locally on this device. No online services are used.",Vector2(92,526),Vector2(455,35),11,Color(0.49,0.66,0.69))
 _button(page_root,"BACK",Vector2(92,606),Vector2(130,38),_show_main)

func _start_match() -> void:
 _save_profile()
 _set_status("LOADING BLACKTIDE PORT  /  LOCAL MATCH")
 var error := get_tree().change_scene_to_file("res://scenes/match.tscn")
 if error != OK:
  _set_status("MATCH SCENE FAILED TO LOAD  /  "+str(error))

func _quit_game() -> void:
 get_tree().quit()

func _set_status(value:String) -> void:
 if is_instance_valid(status_line):
  status_line.text=value

func _panel(parent:Control,pos:Vector2,dimensions:Vector2) -> PanelContainer:
 var panel:=PanelContainer.new()
 panel.position=pos
 panel.size=dimensions
 var style:=StyleBoxFlat.new()
 style.bg_color=Color(0.018,0.035,0.047,0.96)
 style.border_color=Color(0.08,0.33,0.37,0.9)
 style.set_border_width_all(1)
 style.corner_radius_top_left=12
 style.corner_radius_top_right=12
 style.corner_radius_bottom_left=12
 style.corner_radius_bottom_right=12
 panel.add_theme_stylebox_override("panel",style)
 parent.add_child(panel)
 return panel

func _label(parent:Control,value:String,pos:Vector2,dimensions:Vector2,font_size:int,tint:Color,
 bold:bool=false,alignment:HorizontalAlignment=HORIZONTAL_ALIGNMENT_LEFT) -> Label:
 var label:=Label.new()
 label.text=value
 label.position=pos
 label.size=dimensions
 label.horizontal_alignment=alignment
 label.vertical_alignment=VERTICAL_ALIGNMENT_CENTER
 label.add_theme_font_size_override("font_size",font_size)
 label.add_theme_color_override("font_color",tint)
 if bold:
  label.add_theme_color_override("font_shadow_color",Color(0.0,0.025,0.035,0.75))
  label.add_theme_constant_override("shadow_offset_x",1)
  label.add_theme_constant_override("shadow_offset_y",1)
 parent.add_child(label)
 return label

func _button(parent:Control,value:String,pos:Vector2,dimensions:Vector2,action:Callable,accent:bool=false) -> Button:
 var button:=Button.new()
 button.text=value
 button.position=pos
 button.size=dimensions
 button.focus_mode=Control.FOCUS_NONE
 button.add_theme_font_size_override("font_size",16)
 _style_button(button,accent)
 button.pressed.connect(action)
 parent.add_child(button)
 return button

func _style_button(button:Button,selected:bool=false) -> void:
 var normal:=StyleBoxFlat.new()
 normal.bg_color=Color(0.035,0.105,0.13,0.98) if not selected else Color(0.045,0.29,0.31,0.98)
 normal.border_color=Color(0.12,0.47,0.50,0.9) if not selected else Color(0.28,0.89,0.83,1.0)
 normal.set_border_width_all(1 if not selected else 2)
 normal.corner_radius_top_left=8
 normal.corner_radius_top_right=8
 normal.corner_radius_bottom_left=8
 normal.corner_radius_bottom_right=8
 button.add_theme_stylebox_override("normal",normal)
 var hover:=normal.duplicate() as StyleBoxFlat
 hover.bg_color=normal.bg_color.lightened(0.18)
 button.add_theme_stylebox_override("hover",hover)
 button.add_theme_color_override("font_color",Color(0.88,0.96,0.95))
 button.add_theme_color_override("font_hover_color",Color.WHITE)
 button.add_theme_color_override("font_pressed_color",Color(0.34,1.0,0.92))
