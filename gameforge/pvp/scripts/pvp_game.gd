extends Node3D
class_name PVPGame

const ActorScript = preload("res://scripts/pvp_actor.gd")
const BotScript = preload("res://scripts/pvp_bot_brain.gd")
const TouchOverlayScript = preload("res://scripts/pvp_touch_overlay.gd")
const CHARACTER_IDS := ["Aster", "Bront", "Koro", "Luma", "Miri", "Nyx", "Orin", "Pika", "Sola", "Vey"]
const MAP_PATH := "res://assets/map/GAMEFORGE_BlackTide_Port.glb"
const PLAYER_SPAWN := Vector3(-84.0, 1.0, 0.0)
const RIVAL_SPAWN := Vector3(84.0, 1.0, 0.0)

var player: PVPActor
var rival: PVPActor
var rival_brain: PVPBotBrain
var cover_positions: Array[Vector3] = []
var player_score := 0
var rival_score := 0
var round_over := false
var fire_held := false
var settings_open := false
var look_sensitivity := 1.0
var invert_look_y := false
var aim_assist_enabled := true
var master_volume := 0.82
var quality_profile := "BALANCED"
var target_fps := 60
var match_seconds := 180.0
var left_touch_index := -1
var right_touch_index := -1
var left_touch_origin := Vector2.ZERO
var right_touch_origin := Vector2.ZERO
var right_touch_moved := false
var double_tap_time := -10.0
var touch_hud: Control
var timer_label: Label
var settings_button: Button
var settings_panel: PanelContainer
var hud_root: Control
var held_movement := {"forward": false, "back": false, "left": false, "right": false}
var hud_layer: CanvasLayer
var player_health_bar: ProgressBar
var rival_health_bar: ProgressBar
var status_label: Label
var weapon_label: Label
var ammo_label: Label
var score_label: Label
var rematch_button: Button
var flash_overlay: ColorRect
var emote_index := 0

func _ready() -> void:
	randomize()
	_load_settings()
	Engine.max_fps = target_fps
	_apply_audio_volume()
	_apply_quality_profile()
	_build_combat_map()
	_spawn_match()
	_build_hud()
	_update_hud()
	set_process(true)
func _process(delta: float) -> void:
	if settings_open or round_over or not is_instance_valid(player):
		return
	if fire_held:
		player.fire_at_position(_get_aim_point_with_assist())
	match_seconds = maxf(0.0, match_seconds - delta)
	if match_seconds <= 0.0:
		_finish_match()
	_update_hud()
func _input(event: InputEvent) -> void:
	if settings_open:
		return
	if event is InputEventScreenTouch:
		_handle_screen_touch(event as InputEventScreenTouch)
	elif event is InputEventScreenDrag:
		_handle_screen_drag(event as InputEventScreenDrag)
	elif event is InputEventMouseButton:
		var mouse_event := event as InputEventMouseButton
		if mouse_event.button_index == MOUSE_BUTTON_LEFT:
			fire_held = mouse_event.pressed
		elif mouse_event.button_index == MOUSE_BUTTON_RIGHT and mouse_event.pressed:
			Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
		elif mouse_event.button_index == MOUSE_BUTTON_WHEEL_UP and mouse_event.pressed and player:
			player.cycle_weapon(1)
		elif mouse_event.button_index == MOUSE_BUTTON_WHEEL_DOWN and mouse_event.pressed and player:
			player.cycle_weapon(-1)
	elif event is InputEventMouseMotion:
		if Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED and player:
			player.apply_look_delta((event as InputEventMouseMotion).relative)
	elif event.is_action_pressed("pause_game"):
		_toggle_settings()
	elif event.is_action_pressed("reload_weapon"):
		_reload_weapon()
	elif event.is_action_pressed("next_weapon") and player:
		player.cycle_weapon(1)
	elif event.is_action_pressed("previous_weapon") and player:
		player.cycle_weapon(-1)
	elif event.is_action_pressed("jump") and player:
		player.request_jump()
	elif event.is_action_pressed("roll") and player:
		player.request_roll()
	elif event.is_action_pressed("sprint") and player:
		player.set_sprint(true)
	elif event.is_action_released("sprint") and player:
		player.set_sprint(false)
	elif event.is_action_pressed("crouch") and player:
		player.set_crouch(true)
	elif event.is_action_released("crouch") and player:
		player.set_crouch(false)
	elif event.is_action_pressed("flash_grenade"):
		_activate_flash()
	elif event.is_action_pressed("cyber_shield"):
		_activate_shield()
func _build_combat_map() -> void:
	if not ResourceLoader.exists(MAP_PATH):
		push_error("BLACKTIDE Port is missing. Build the Blender assets before running.")
		return
	var packed := load(MAP_PATH) as PackedScene
	if packed == null:
		push_error("BLACKTIDE Port GLB is invalid.")
		return
	var world := packed.instantiate() as Node3D
	world.name = "BLACKTIDE_Port_Environment"
	world.position = Vector3.ZERO
	world.rotation = Vector3.ZERO
	world.scale = Vector3.ONE
	add_child(world)
	var collision_count := _create_map_collisions(world)
	if collision_count < 25:
		push_error("Playable world collision gate failed: found only %d collision meshes." % collision_count)
	var environment := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = Sky.new()
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.24, 0.31, 0.36)
	env.ambient_light_energy = 0.72
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.fog_enabled = true
	env.fog_light_color = Color(0.22, 0.28, 0.32)
	env.fog_density = 0.0012
	environment.environment = env
	add_child(environment)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-49.0, -32.0, 0.0)
	sun.light_energy = 1.35
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 115.0
	add_child(sun)
	cover_positions = [
		Vector3(-53,1,-38),Vector3(-37,1,43),Vector3(-18,1,-52),Vector3(-6,1,35),
		Vector3(14,1,-39),Vector3(31,1,45),Vector3(51,1,-25),Vector3(60,1,27),
		Vector3(-65,1,8),Vector3(70,1,-8),Vector3(-29,1,4),Vector3(28,1,-2),
		Vector3(-88,1,-35),Vector3(90,1,17),Vector3(-42,1,82),Vector3(36,1,-96)
	]

func _create_map_collisions(root: Node) -> int:
	var created := 0
	for child in root.get_children():
		if child is MeshInstance3D:
			var mesh := child as MeshInstance3D
			if mesh.mesh != null:
				var body := StaticBody3D.new()
				body.name = mesh.name + "_Collision"
				body.global_transform = mesh.global_transform
				var shape := CollisionShape3D.new()
				var box := BoxShape3D.new()
				var bounds := mesh.get_aabb()
				box.size = bounds.size
				shape.shape = box
				shape.position = bounds.get_center()
				body.add_child(shape)
				add_child(body)
				created += 1
		created += _create_map_collisions(child)
	return created
func _add_cover(label: String, position: Vector3, dimensions: Vector3, tint: Color) -> void:
	var body := StaticBody3D.new()
	body.name = label
	body.position = position + Vector3(0.0, dimensions.y * 0.5, 0.0)
	add_child(body)
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = dimensions
	shape.shape = box
	body.add_child(shape)
	var visual := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = dimensions
	visual.mesh = mesh
	var material := StandardMaterial3D.new()
	material.albedo_color = tint
	material.roughness = 0.68
	material.metallic = 0.22
	visual.material_override = material
	body.add_child(visual)

func _spawn_match() -> void:
	var profile := ConfigFile.new()
	profile.load("user://blacktide_profile.cfg")
	var player_id := str(profile.get_value("profile","operator","Aster"))
	if not CHARACTER_IDS.has(player_id):
		player_id = "Aster"
	var selected_weapon := clampi(int(profile.get_value("profile","weapon",2)),0,PVPActor.WEAPONS.size()-1)
	var rival_id: String = CHARACTER_IDS[randi() % CHARACTER_IDS.size()]
	while rival_id == player_id:
		rival_id = CHARACTER_IDS[randi() % CHARACTER_IDS.size()]
	player = _spawn_fighter("Player",player_id,true,PLAYER_SPAWN)
	player.set_weapon(selected_weapon)
	rival = _spawn_fighter("Rival",rival_id,false,RIVAL_SPAWN)
	rival_brain = BotScript.new() as PVPBotBrain
	rival_brain.actor = rival
	rival_brain.target = player
	rival_brain.game_root = self
	rival.add_child(rival_brain)
	player.defeated.connect(_on_fighter_defeated)
	rival.defeated.connect(_on_fighter_defeated)
	player.health_changed.connect(_on_actor_health_changed)
	rival.health_changed.connect(_on_actor_health_changed)
	player.weapon_changed.connect(_on_player_weapon_changed)
	player.ammo_changed.connect(_on_player_ammo_changed)
func _spawn_fighter(label: String, character: String, user_controlled: bool, spawn: Vector3) -> PVPActor:
	var fighter := ActorScript.new() as PVPActor
	fighter.name = label
	fighter.is_player = user_controlled
	fighter.character_id = character
	fighter.game_root = self
	fighter.position = spawn
	add_child(fighter)
	return fighter

func _build_hud() -> void:
	hud_layer = CanvasLayer.new()
	hud_layer.name = "BLACKTIDE_HUD"
	add_child(hud_layer)
	hud_root = Control.new()
	hud_root.name = "HUDRoot"
	hud_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	hud_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud_layer.add_child(hud_root)
	score_label = _make_label(hud_root,"BLACKTIDE  /  TACTICAL DUEL",Vector2(34,22),Vector2(520,34),22)
	status_label = _make_label(hud_root,"ELIMINATE THE HOSTILE",Vector2(34,60),Vector2(500,28),16)
	timer_label = _make_label(hud_root,"03:00",Vector2(590,22),Vector2(100,34),24)
	player_health_bar = _make_bar(hud_root,Vector2(34,110),Vector2(300,16),Color(0.23,0.79,0.73))
	_make_label(hud_root,"OPERATOR",Vector2(34,130),Vector2(140,20),13)
	rival_health_bar = _make_bar(hud_root,Vector2(930,42),Vector2(250,14),Color(0.94,0.39,0.26))
	_make_label(hud_root,"HOSTILE",Vector2(930,20),Vector2(130,18),13)
	settings_button = _add_tap_button(hud_root,"⚙",Vector2(1190,18),Vector2(58,58),_toggle_settings)
	settings_button.add_theme_font_size_override("font_size",28)
	var ammo_card := PanelContainer.new()
	ammo_card.position = Vector2(685,606)
	ammo_card.size = Vector2(280,76)
	var card_style := StyleBoxFlat.new()
	card_style.bg_color = Color(0.018,0.038,0.048,0.82)
	card_style.border_color = Color(0.2,0.61,0.62,0.65)
	card_style.set_border_width_all(1)
	card_style.corner_radius_top_left = 9
	card_style.corner_radius_top_right = 9
	card_style.corner_radius_bottom_left = 9
	card_style.corner_radius_bottom_right = 9
	ammo_card.add_theme_stylebox_override("panel",card_style)
	hud_root.add_child(ammo_card)
	weapon_label = _make_label(ammo_card,"AEGIS AR",Vector2(14,8),Vector2(245,25),17)
	ammo_label = _make_label(ammo_card,"30 / 150",Vector2(14,37),Vector2(245,25),21)
	_make_label(hud_root,"LEFT THUMB  MOVE    •    RIGHT THUMB  AIM",Vector2(335,680),Vector2(330,18),11,HORIZONTAL_ALIGNMENT_CENTER)
	_add_action_button(hud_root,"ROLL",Vector2(994,414),Vector2(82,56),Callable(self,"_request_roll"),Callable(self,"_release_action"))
	_add_action_button(hud_root,"CROUCH",Vector2(1082,414),Vector2(88,56),Callable(self,"_set_crouch_button").bind(true),Callable(self,"_set_crouch_button").bind(false))
	_add_tap_button(hud_root,"JUMP",Vector2(1176,414),Vector2(82,56),_request_jump)
	_add_action_button(hud_root,"FIRE",Vector2(1090,486),Vector2(168,92),Callable(self,"_set_fire").bind(true),Callable(self,"_set_fire").bind(false))
	_add_tap_button(hud_root,"FLASH",Vector2(994,486),Vector2(82,56),_activate_flash)
	_add_tap_button(hud_root,"SHIELD",Vector2(994,550),Vector2(82,56),_activate_shield)
	_add_tap_button(hud_root,"RELOAD",Vector2(1082,588),Vector2(88,54),_reload_weapon)
	_add_tap_button(hud_root,"WEAPON",Vector2(1176,588),Vector2(82,54),_next_weapon)
	_add_tap_button(hud_root,"EMOTE",Vector2(994,614),Vector2(82,46),_cycle_emote)
	touch_hud = TouchOverlayScript.new() as Control
	touch_hud.name = "TouchAimAndMovementOverlay"
	touch_hud.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	touch_hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud_root.add_child(touch_hud)
	rematch_button = _add_tap_button(hud_root,"REMATCH",Vector2(510,342),Vector2(260,78),_start_rematch)
	rematch_button.visible = false
	flash_overlay = ColorRect.new()
	flash_overlay.color = Color(1.0,1.0,1.0,0.0)
	flash_overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	flash_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud_root.add_child(flash_overlay)
	_build_settings_panel()

func _build_settings_panel() -> void:
	settings_panel = PanelContainer.new()
	settings_panel.name = "CombatSettings"
	settings_panel.position = Vector2(355,86)
	settings_panel.size = Vector2(570,548)
	settings_panel.visible = false
	settings_panel.mouse_filter = Control.MOUSE_FILTER_STOP
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.014,0.03,0.044,0.985)
	style.border_color = Color(0.16,0.63,0.66,0.95)
	style.set_border_width_all(2)
	style.corner_radius_top_left = 14
	style.corner_radius_top_right = 14
	style.corner_radius_bottom_left = 14
	style.corner_radius_bottom_right = 14
	settings_panel.add_theme_stylebox_override("panel",style)
	hud_root.add_child(settings_panel)
	var layout := VBoxContainer.new()
	layout.add_theme_constant_override("separation",11)
	layout.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	layout.size_flags_vertical = Control.SIZE_EXPAND_FILL
	settings_panel.add_child(layout)
	var title := Label.new()
	title.text = "COMBAT SETTINGS"
	title.add_theme_font_size_override("font_size",25)
	title.add_theme_color_override("font_color",Color(0.82,0.97,0.94))
	layout.add_child(title)
	var sens_label := Label.new()
	sens_label.text = "LOOK SENSITIVITY  •  %.2fx" % look_sensitivity
	layout.add_child(sens_label)
	var sens := HSlider.new()
	sens.min_value = 0.45
	sens.max_value = 2.4
	sens.step = 0.05
	sens.value = look_sensitivity
	sens.custom_minimum_size = Vector2(470,28)
	sens.value_changed.connect(func(value: float) -> void:
		look_sensitivity = value
		sens_label.text = "LOOK SENSITIVITY  •  %.2fx" % value
		_save_settings()
	)
	layout.add_child(sens)
	var volume_label := Label.new()
	volume_label.text = "MASTER VOLUME  •  %d%%" % int(master_volume*100.0)
	layout.add_child(volume_label)
	var volume := HSlider.new()
	volume.min_value = 0.0
	volume.max_value = 1.0
	volume.step = 0.01
	volume.value = master_volume
	volume.custom_minimum_size = Vector2(470,28)
	volume.value_changed.connect(func(value: float) -> void:
		master_volume = value
		volume_label.text = "MASTER VOLUME  •  %d%%" % int(value*100.0)
		_apply_audio_volume()
		_save_settings()
	)
	layout.add_child(volume)
	var invert := CheckBox.new()
	invert.text = "Invert vertical look"
	invert.button_pressed = invert_look_y
	invert.toggled.connect(func(value: bool) -> void:
		invert_look_y = value
		_save_settings()
	)
	layout.add_child(invert)
	var aim := CheckBox.new()
	aim.text = "Soft aim assist"
	aim.button_pressed = aim_assist_enabled
	aim.toggled.connect(func(value: bool) -> void:
		aim_assist_enabled = value
		_save_settings()
	)
	layout.add_child(aim)
	var quality_label := Label.new()
	quality_label.text = "GRAPHICS PROFILE"
	layout.add_child(quality_label)
	var quality := OptionButton.new()
	quality.add_item("LOW  •  30 FPS")
	quality.add_item("BALANCED  •  45 FPS")
	quality.add_item("HIGH  •  60 FPS")
	quality.select(1 if quality_profile=="BALANCED" else (2 if quality_profile=="HIGH" else 0))
	quality.item_selected.connect(func(index: int) -> void:
		quality_profile = ["LOW","BALANCED","HIGH"][index]
		target_fps = [30,45,60][index]
		Engine.max_fps = target_fps
		_apply_quality_profile()
		_save_settings()
	)
	layout.add_child(quality)
	var help := Label.new()
	help.text = "TOUCH: left thumb steers; right thumb aims and fires.\nSwipe up/down for abilities, swipe sideways to change weapon.\nDESKTOP: WASD, mouse, R reload, Q/E weapons, Shift sprint, C crouch, Space jump, V roll."
	help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	help.custom_minimum_size = Vector2(470,75)
	help.add_theme_color_override("font_color",Color(0.59,0.74,0.76))
	layout.add_child(help)
	var close := Button.new()
	close.text = "SAVE & RESUME"
	close.custom_minimum_size = Vector2(470,46)
	_style_button(close,Color(0.07,0.26,0.29,0.98))
	close.pressed.connect(_toggle_settings)
	layout.add_child(close)
	var main_menu := Button.new()
	main_menu.text = "EXIT TO MAIN MENU"
	main_menu.custom_minimum_size = Vector2(470,42)
	_style_button(main_menu,Color(0.10,0.18,0.22,0.98))
	main_menu.pressed.connect(_return_to_main_menu)
	layout.add_child(main_menu)

func _toggle_settings() -> void:
	settings_open = not settings_open
	if is_instance_valid(settings_panel):
		settings_panel.visible = settings_open
	if settings_button:
		settings_button.text = "×" if settings_open else "⚙"
	if settings_open:
		fire_held = false
		if player:
			player.set_move_input(Vector2.ZERO)
			player.set_sprint(false)
		if is_instance_valid(rival_brain):
			rival_brain.set_physics_process(false)
		Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
	else:
		if is_instance_valid(rival_brain):
			rival_brain.set_physics_process(true)

func _load_settings() -> void:
	var config := ConfigFile.new()
	if config.load("user://blacktide_pvp.cfg") != OK:
		return
	look_sensitivity = float(config.get_value("controls","look_sensitivity",1.0))
	invert_look_y = bool(config.get_value("controls","invert_look_y",false))
	aim_assist_enabled = bool(config.get_value("controls","aim_assist",true))
	master_volume = float(config.get_value("audio","master_volume",0.82))
	quality_profile = str(config.get_value("video","quality","BALANCED"))
	target_fps = int(config.get_value("video","fps",60))

func _save_settings() -> void:
	var config := ConfigFile.new()
	config.set_value("controls","look_sensitivity",look_sensitivity)
	config.set_value("controls","invert_look_y",invert_look_y)
	config.set_value("controls","aim_assist",aim_assist_enabled)
	config.set_value("audio","master_volume",master_volume)
	config.set_value("video","quality",quality_profile)
	config.set_value("video","fps",target_fps)
	config.save("user://blacktide_pvp.cfg")

func _apply_audio_volume() -> void:
	var master := AudioServer.get_bus_index("Master")
	if master >= 0:
		AudioServer.set_bus_volume_db(master,linear_to_db(maxf(0.001,master_volume)))

func _apply_quality_profile() -> void:
	if quality_profile=="LOW":
		get_viewport().msaa_3d = Viewport.MSAA_DISABLED
	elif quality_profile=="BALANCED":
		get_viewport().msaa_3d = Viewport.MSAA_2X
	else:
		get_viewport().msaa_3d = Viewport.MSAA_4X
func _physics_process(_delta: float) -> void:
	if not player or round_over or settings_open or left_touch_index >= 0:
		return
	player.set_move_input(Input.get_vector("move_left","move_right","move_forward","move_back"))

func _handle_screen_touch(touch: InputEventScreenTouch) -> void:
	if touch.position.x >= 980.0 and touch.position.y >= 400.0:
		return
	var view_size := get_viewport().get_visible_rect().size
	if touch.pressed:
		if touch.position.x > view_size.x-96.0 and touch.position.y < 92.0:
			return
		if touch.position.x < view_size.x*0.43 and touch.position.y > view_size.y*0.28:
			left_touch_index = touch.index
			left_touch_origin = touch.position
			_update_thumb_stick(touch.position,true)
		elif touch.position.x > view_size.x*0.48 and touch.position.y < view_size.y*0.66:
			right_touch_index = touch.index
			right_touch_origin = touch.position
			right_touch_moved = false
			fire_held = true
		elif touch.position.x > view_size.x*0.70 and touch.position.y >= view_size.y*0.66:
			right_touch_index = touch.index
			right_touch_origin = touch.position
			right_touch_moved = false
			fire_held = false
	else:
		if touch.index == left_touch_index:
			left_touch_index = -1
			if player:
				player.set_move_input(Vector2.ZERO)
				player.set_sprint(false)
			_update_thumb_stick(Vector2.ZERO,false)
		elif touch.index == right_touch_index:
			var swipe := touch.position-right_touch_origin
			right_touch_index = -1
			fire_held = false
			if absf(swipe.x)>86.0 and absf(swipe.x)>absf(swipe.y)*1.15:
				if player:
					player.cycle_weapon(1 if swipe.x>0.0 else -1)
			elif absf(swipe.y)>78.0 and absf(swipe.y)>absf(swipe.x)*1.1:
				if swipe.y<0.0:
					_activate_flash()
				else:
					_activate_shield()
			elif not right_touch_moved:
				var now := Time.get_ticks_msec()/1000.0
				if now-double_tap_time<0.33:
					_reload_weapon()
					double_tap_time=-10.0
				else:
					double_tap_time=now

func _handle_screen_drag(drag: InputEventScreenDrag) -> void:
	if drag.index == left_touch_index:
		_update_thumb_stick(drag.position,true)
	elif drag.index==right_touch_index and player:
		if drag.position.distance_to(right_touch_origin)>12.0:
			right_touch_moved=true
		player.apply_look_delta(drag.screen_relative)
		if aim_assist_enabled:
			_soft_aim_assist()

func _update_thumb_stick(pointer: Vector2,active: bool) -> void:
	if not player or not active:
		if touch_hud:
			touch_hud.call("update_stick",false,Vector2(132,574),Vector2(132,574))
		return
	var offset := (pointer-left_touch_origin).limit_length(84.0)
	var control := offset/84.0
	player.set_move_input(control)
	player.set_sprint(control.length()>0.88)
	if touch_hud:
		touch_hud.call("update_stick",true,left_touch_origin,left_touch_origin+offset)

func _get_aim_point_with_assist() -> Vector3:
	var point := player.get_aim_point()
	if not aim_assist_enabled or not rival or not player.camera:
		return point
	var direction := rival.global_position+Vector3.UP*1.3-player.global_position-Vector3.UP*1.4
	if direction.length()<42.0 and (-player.camera.global_basis.z).dot(direction.normalized())>0.965:
		return rival.global_position+Vector3.UP*1.3
	return point

func _soft_aim_assist() -> void:
	if not rival or not player.camera:
		return
	var direction := (rival.global_position+Vector3.UP*1.3-player.camera.global_position).normalized()
	if (-player.camera.global_basis.z).dot(direction)>0.982:
		player.camera_yaw=lerp_angle(player.camera_yaw,atan2(-direction.x,-direction.z),0.018)
		player.camera_pivot.rotation.y=player.camera_yaw

func _on_actor_health_changed(_actor: PVPActor,_current: float,_maximum: float) -> void:
	_update_hud()

func _on_player_weapon_changed(_actor: PVPActor,_weapon_name: String) -> void:
	_update_hud()

func _on_player_ammo_changed(_actor: PVPActor,_current: int,_reserve: int) -> void:
	_update_hud()

func _finish_match() -> void:
	if round_over:
		return
	round_over=true
	fire_held=false
	status_label.text="MATCH COMPLETE  •  DRAW" if player_score==rival_score else ("MATCH COMPLETE  •  VICTORY" if player_score>rival_score else "MATCH COMPLETE  •  DEFEAT")
	rematch_button.visible=true

func _make_label(parent: Control, value: String, position: Vector2, dimensions: Vector2, font_size: int, alignment: HorizontalAlignment = HORIZONTAL_ALIGNMENT_LEFT) -> Label:
	var label := Label.new()
	label.text = value
	label.position = position
	label.size = dimensions
	label.horizontal_alignment = alignment
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", Color(0.91, 0.96, 0.94))
	label.add_theme_color_override("font_shadow_color", Color(0.01, 0.04, 0.05, 0.9))
	label.add_theme_constant_override("shadow_offset_x", 2)
	label.add_theme_constant_override("shadow_offset_y", 2)
	parent.add_child(label)
	return label

func _make_bar(parent: Control, position: Vector2, dimensions: Vector2, fill_color: Color) -> ProgressBar:
	var bar := ProgressBar.new()
	bar.position = position
	bar.size = dimensions
	bar.min_value = 0
	bar.max_value = 100
	bar.value = 100
	bar.show_percentage = false
	var fill := StyleBoxFlat.new()
	fill.bg_color = fill_color
	fill.corner_radius_top_left = 7
	fill.corner_radius_top_right = 7
	fill.corner_radius_bottom_left = 7
	fill.corner_radius_bottom_right = 7
	bar.add_theme_stylebox_override("fill", fill)
	var background := StyleBoxFlat.new()
	background.bg_color = Color(0.025, 0.055, 0.065, 0.92)
	background.corner_radius_top_left = 7
	background.corner_radius_top_right = 7
	background.corner_radius_bottom_left = 7
	background.corner_radius_bottom_right = 7
	bar.add_theme_stylebox_override("background", background)
	parent.add_child(bar)
	return bar

func _add_action_button(parent: Control, caption: String, position: Vector2, dimensions: Vector2, pressed: Callable, released: Callable) -> Button:
	var button := Button.new()
	button.text = caption
	button.position = position
	button.size = dimensions
	button.focus_mode = Control.FOCUS_NONE
	button.add_theme_font_size_override("font_size", 19)
	_style_button(button, Color(0.06, 0.18, 0.22, 0.90))
	button.button_down.connect(pressed)
	button.button_up.connect(released)
	parent.add_child(button)
	return button

func _add_tap_button(parent: Control, caption: String, position: Vector2, dimensions: Vector2, action: Callable) -> Button:
	var button := Button.new()
	button.text = caption
	button.position = position
	button.size = dimensions
	button.focus_mode = Control.FOCUS_NONE
	button.add_theme_font_size_override("font_size", 17)
	_style_button(button, Color(0.09, 0.22, 0.25, 0.92))
	button.pressed.connect(action)
	parent.add_child(button)
	return button

func _style_button(button: Button, tint: Color) -> void:
	var normal := StyleBoxFlat.new()
	normal.bg_color = tint
	normal.border_color = Color(0.22, 0.78, 0.78, 0.88)
	normal.set_border_width_all(2)
	normal.corner_radius_top_left = 12
	normal.corner_radius_top_right = 12
	normal.corner_radius_bottom_left = 12
	normal.corner_radius_bottom_right = 12
	button.add_theme_stylebox_override("normal", normal)
	var hover := normal.duplicate() as StyleBoxFlat
	hover.bg_color = tint.lightened(0.16)
	button.add_theme_stylebox_override("hover", hover)
	button.add_theme_color_override("font_color", Color(0.94, 0.98, 0.98))
	button.add_theme_color_override("font_hover_color", Color.WHITE)

func _set_move(direction: String, pressed: bool) -> void:
	held_movement[direction] = pressed
	var x := float(held_movement["right"]) - float(held_movement["left"])
	var y := float(held_movement["back"]) - float(held_movement["forward"])
	if player:
		player.set_move_input(Vector2(x, y).limit_length(1.0))

func _set_fire(pressed: bool) -> void:
	fire_held = pressed

func _activate_flash() -> void:
	if player and not round_over:
		player.throw_flash_grenade(player.get_aim_point(28.0))

func _activate_shield() -> void:
	if player and not round_over:
		player.activate_cyber_shield()

func _reload_weapon() -> void:
	if player:
		player.reload_weapon()

func _next_weapon() -> void:
	if player and not round_over:
		player.cycle_weapon()

func _emote_wave() -> void:
	if player:
		player.play_emote("Emote_Wave")

func _emote_guard() -> void:
	if player:
		player.play_emote("Emote_Guard")

func _emote_victory() -> void:
	if player:
		player.play_emote("Emote_Victory")

func _cycle_emote() -> void:
	if not player:
		return
	var clips := ["Emote_Wave","Emote_Guard","Emote_Victory"]
	player.play_emote(clips[emote_index])
	emote_index = (emote_index + 1) % clips.size()

func _request_jump() -> void:
	if player and not round_over:
		player.request_jump()

func _request_roll() -> void:
	if player and not round_over:
		player.request_roll()

func _set_crouch_button(pressed: bool) -> void:
	if player and not round_over:
		player.set_crouch(pressed)

func _release_action() -> void:
	pass

func _return_to_main_menu() -> void:
	get_tree().change_scene_to_file("res://scenes/main.tscn")

func get_cover_positions() -> Array[Vector3]:
	return cover_positions

func throw_flash_grenade(owner: PVPActor, destination: Vector3) -> void:
	var grenade := Node3D.new()
	grenade.name = "FlashGrenade"
	var visual := MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 0.16
	sphere.height = 0.32
	visual.mesh = sphere
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(0.8, 0.94, 1.0)
	material.emission_enabled = true
	material.emission = Color(0.25, 0.8, 1.0)
	material.emission_energy_multiplier = 3.0
	visual.material_override = material
	grenade.add_child(visual)
	grenade.global_position = owner.global_position + Vector3.UP * 1.25
	add_child(grenade)
	var landing := destination + Vector3.UP * 0.25
	var tween := create_tween()
	tween.tween_property(grenade, "global_position", landing, 0.72).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tween.tween_callback(Callable(self, "_detonate_flash").bind(grenade, owner))

func _detonate_flash(grenade: Node3D, owner: PVPActor) -> void:
	if not is_instance_valid(grenade):
		return
	var center := grenade.global_position
	for fighter in get_tree().get_nodes_in_group("pvp_fighters"):
		if fighter == owner or not (fighter is PVPActor):
			continue
		var target_actor := fighter as PVPActor
		var distance := center.distance_to(target_actor.global_position + Vector3.UP)
		if distance > 11.0:
			continue
		var query := PhysicsRayQueryParameters3D.create(center, target_actor.global_position + Vector3.UP)
		query.exclude = [owner.get_rid()]
		query.collision_mask = 1
		var hit := get_world_3d().direct_space_state.intersect_ray(query)
		if hit.is_empty() or hit.get("collider") == target_actor:
			target_actor.apply_flash(2.75 * (1.0 - distance / 14.0))
	grenade.queue_free()

func show_shot_effect(start: Vector3, finish: Vector3) -> void:
	var mesh := ImmediateMesh.new()
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_color = Color(0.28, 0.93, 1.0)
	material.emission_enabled = true
	material.emission = Color(0.15, 0.8, 1.0)
	material.emission_energy_multiplier = 2.0
	mesh.surface_begin(Mesh.PRIMITIVE_LINES, material)
	mesh.surface_add_vertex(start)
	mesh.surface_add_vertex(finish)
	mesh.surface_end()
	var tracer := MeshInstance3D.new()
	tracer.mesh = mesh
	add_child(tracer)
	var tween := create_tween()
	tween.tween_interval(0.065)
	tween.tween_callback(tracer.queue_free)

func show_flash_overlay(duration: float) -> void:
	if not is_instance_valid(flash_overlay):
		return
	var tween := create_tween()
	flash_overlay.color = Color(1.0, 1.0, 1.0, 0.78)
	tween.tween_property(flash_overlay, "color", Color(1.0, 1.0, 1.0, 0.0), maxf(0.35, duration))

func _on_fighter_defeated(loser: PVPActor) -> void:
	if round_over:
		return
	round_over = true
	fire_held = false
	player.set_move_input(Vector2.ZERO)
	if loser == rival:
		player_score += 1
		status_label.text = "VICTORY  •  RIVAL ELIMINATED"
		player.play_emote("Emote_Victory")
	else:
		rival_score += 1
		status_label.text = "DEFEAT  •  RIVAL WINS"
	rematch_button.visible = true
	_update_hud()

func _start_rematch() -> void:
	if not round_over:
		return
	round_over = false
	match_seconds = 180.0
	rematch_button.visible = false
	status_label.text = "NEW ROUND  •  BLACKTIDE PORT"
	player.reset_for_rematch(PLAYER_SPAWN)
	rival.reset_for_rematch(RIVAL_SPAWN)
	rival_brain.cover_position = Vector3.ZERO
	rival_brain.state = "SCAN"
	rival_brain.last_weapon = -1
	rival_brain.grenade_cooldown = 0.0
	_update_hud()
func _update_hud() -> void:
	if not is_instance_valid(player):
		return
	if player_health_bar:
		player_health_bar.value = player.health
	if rival_health_bar and rival:
		rival_health_bar.value = rival.health
	if weapon_label:
		weapon_label.text = str(PVPActor.WEAPONS[player.current_weapon]["name"]).to_upper()
	if ammo_label:
		ammo_label.text = "%02d   /   %03d" % [player.ammunition,player.reserve_ammunition]
	if score_label:
		score_label.text = "BLACKTIDE  /  YOU %d  —  HOSTILE %d  /  1v1" % [player_score,rival_score]
	if timer_label:
		var mins := int(match_seconds)/60
		var secs := int(match_seconds)%60
		timer_label.text = "%02d:%02d" % [mins,secs]
