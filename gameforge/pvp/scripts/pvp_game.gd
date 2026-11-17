extends Node3D
class_name PVPGame

const ActorScript = preload("res://scripts/pvp_actor.gd")
const BotScript = preload("res://scripts/pvp_bot_brain.gd")
const CHARACTER_IDS := ["Aster", "Bront", "Koro", "Luma", "Miri", "Nyx", "Orin", "Pika", "Sola", "Vey"]
const ARENA_SIZE := 68.0
const FLOOR_Y := 1.0

var player: PVPActor
var rival: PVPActor
var rival_brain: PVPBotBrain
var cover_positions: Array[Vector3] = []
var player_score := 0
var rival_score := 0
var round_over := false
var fire_held := false
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

func _ready() -> void:
	randomize()
	Engine.max_fps = 30
	_build_combat_map()
	_spawn_match()
	_build_hud()
	_update_hud()

func _process(_delta: float) -> void:
	if round_over or not is_instance_valid(player):
		return
	if fire_held:
		player.fire_at_position(player.get_aim_point())
	_update_hud()

func _input(event: InputEvent) -> void:
	if event is InputEventScreenDrag:
		var drag := event as InputEventScreenDrag
		var size := get_viewport().get_visible_rect().size
		if drag.position.x > size.x * 0.43 and drag.position.y < size.y * 0.72 and drag.position.y > 38.0:
			if player:
				player.apply_look_delta(drag.relative)
	elif event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
		if player:
			player.apply_look_delta((event as InputEventMouseMotion).relative)

func _build_combat_map() -> void:
	var world_path := "res://assets/map/GAMEFORGE_Loomwild_Environment.glb"
	if ResourceLoader.exists(world_path):
		var world_packed := load(world_path) as PackedScene
		if world_packed:
			var world := world_packed.instantiate() as Node3D
			world.name = "LoomwildWorldVisuals"
			world.position.y = 0.7
			world.rotation_degrees.x = 90.0
			world.scale = Vector3.ONE * 0.55
			add_child(world)

	var environment := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = Sky.new()
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.38, 0.49, 0.56)
	env.ambient_light_energy = 0.82
	environment.environment = env
	add_child(environment)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48.0, -28.0, 0.0)
	sun.light_energy = 1.25
	add_child(sun)

	var floor_body := StaticBody3D.new()
	floor_body.name = "CombatArenaFloor"
	floor_body.position = Vector3(0.0, FLOOR_Y - 0.5, 0.0)
	add_child(floor_body)
	var floor_collision := CollisionShape3D.new()
	var floor_shape := BoxShape3D.new()
	floor_shape.size = Vector3(ARENA_SIZE, 1.0, ARENA_SIZE)
	floor_collision.shape = floor_shape
	floor_body.add_child(floor_collision)
	var floor_mesh := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(ARENA_SIZE, ARENA_SIZE)
	floor_mesh.mesh = plane
	var floor_material := StandardMaterial3D.new()
	floor_material.albedo_color = Color(0.075, 0.15, 0.14)
	floor_material.roughness = 0.96
	floor_mesh.material_override = floor_material
	floor_mesh.position.y = 0.505
	floor_body.add_child(floor_mesh)

	var wall_color := Color(0.10, 0.20, 0.22)
	_add_cover("NorthBoundary", Vector3(0.0, FLOOR_Y, -ARENA_SIZE * 0.5), Vector3(ARENA_SIZE, 2.6, 1.0), wall_color)
	_add_cover("SouthBoundary", Vector3(0.0, FLOOR_Y, ARENA_SIZE * 0.5), Vector3(ARENA_SIZE, 2.6, 1.0), wall_color)
	_add_cover("WestBoundary", Vector3(-ARENA_SIZE * 0.5, FLOOR_Y, 0.0), Vector3(1.0, 2.6, ARENA_SIZE), wall_color)
	_add_cover("EastBoundary", Vector3(ARENA_SIZE * 0.5, FLOOR_Y, 0.0), Vector3(1.0, 2.6, ARENA_SIZE), wall_color)
	_add_cover("MidlineCoverA", Vector3(-8.0, FLOOR_Y, -5.0), Vector3(5.0, 1.9, 1.4), Color(0.12, 0.28, 0.30))
	_add_cover("MidlineCoverB", Vector3(8.0, FLOOR_Y, 5.0), Vector3(5.0, 1.9, 1.4), Color(0.12, 0.28, 0.30))
	_add_cover("WestPillarA", Vector3(-19.0, FLOOR_Y, -14.0), Vector3(2.4, 3.2, 2.4), Color(0.18, 0.30, 0.28))
	_add_cover("WestPillarB", Vector3(-19.0, FLOOR_Y, 14.0), Vector3(2.4, 3.2, 2.4), Color(0.18, 0.30, 0.28))
	_add_cover("EastPillarA", Vector3(19.0, FLOOR_Y, -14.0), Vector3(2.4, 3.2, 2.4), Color(0.18, 0.30, 0.28))
	_add_cover("EastPillarB", Vector3(19.0, FLOOR_Y, 14.0), Vector3(2.4, 3.2, 2.4), Color(0.18, 0.30, 0.28))
	_add_cover("NorthLowCover", Vector3(0.0, FLOOR_Y, -19.0), Vector3(8.0, 1.0, 1.2), Color(0.24, 0.34, 0.28))
	_add_cover("SouthLowCover", Vector3(0.0, FLOOR_Y, 19.0), Vector3(8.0, 1.0, 1.2), Color(0.24, 0.34, 0.28))
	_add_cover("WestLowCover", Vector3(-25.0, FLOOR_Y, 0.0), Vector3(1.2, 1.0, 8.0), Color(0.24, 0.34, 0.28))
	_add_cover("EastLowCover", Vector3(25.0, FLOOR_Y, 0.0), Vector3(1.2, 1.0, 8.0), Color(0.24, 0.34, 0.28))
	_add_cover("WestArmory", Vector3(-3.0, FLOOR_Y, 0.0), Vector3(2.4, 1.2, 2.4), Color(0.10, 0.31, 0.35))
	_add_cover("EastArmory", Vector3(3.0, FLOOR_Y, 0.0), Vector3(2.4, 1.2, 2.4), Color(0.10, 0.31, 0.35))
	cover_positions = [
		Vector3(-12.0, FLOOR_Y, 12.0), Vector3(12.0, FLOOR_Y, 12.0),
		Vector3(-12.0, FLOOR_Y, -12.0), Vector3(12.0, FLOOR_Y, -12.0),
		Vector3(-23.0, FLOOR_Y, 8.0), Vector3(23.0, FLOOR_Y, -8.0),
		Vector3(-4.0, FLOOR_Y, -22.0), Vector3(4.0, FLOOR_Y, 22.0)
	]

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
	var player_id: String = CHARACTER_IDS[randi() % CHARACTER_IDS.size()]
	var rival_id: String = CHARACTER_IDS[randi() % CHARACTER_IDS.size()]
	while rival_id == player_id:
		rival_id = CHARACTER_IDS[randi() % CHARACTER_IDS.size()]
	player = _spawn_fighter("Player", player_id, true, Vector3(0.0, FLOOR_Y, 25.0))
	rival = _spawn_fighter("Rival", rival_id, false, Vector3(0.0, FLOOR_Y, -25.0))
	rival_brain = BotScript.new() as PVPBotBrain
	rival_brain.actor = rival
	rival_brain.target = player
	rival_brain.game_root = self
	rival.add_child(rival_brain)
	player.defeated.connect(_on_fighter_defeated)
	rival.defeated.connect(_on_fighter_defeated)

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
	hud_layer.name = "MobileHUD"
	add_child(hud_layer)
	var ui := Control.new()
	ui.name = "HUDRoot"
	ui.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	ui.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud_layer.add_child(ui)
	score_label = _make_label(ui, "LOOMWILD  •  1v1 OFFLINE", Vector2(34, 18), Vector2(520, 42), 27)
	status_label = _make_label(ui, "ELIMINATE THE RIVAL", Vector2(34, 66), Vector2(480, 34), 21)
	weapon_label = _make_label(ui, "AEGIS AR", Vector2(34, 112), Vector2(320, 30), 22)
	ammo_label = _make_label(ui, "30 / AUTO RELOAD", Vector2(34, 146), Vector2(520, 28), 18)
	player_health_bar = _make_bar(ui, Vector2(34, 190), Vector2(290, 20), Color(0.1, 0.78, 0.75))
	rival_health_bar = _make_bar(ui, Vector2(930, 34), Vector2(300, 20), Color(0.94, 0.36, 0.25))
	_make_label(ui, "YOU", Vector2(34, 166), Vector2(80, 22), 15)
	_make_label(ui, "BOT", Vector2(930, 10), Vector2(80, 22), 15)
	_add_action_button(ui, "RUN", Vector2(80, 510), Vector2(112, 76), Callable(self, "_set_move").bind("forward", true), Callable(self, "_set_move").bind("forward", false))
	_add_action_button(ui, "LEFT", Vector2(14, 596), Vector2(105, 76), Callable(self, "_set_move").bind("left", true), Callable(self, "_set_move").bind("left", false))
	_add_action_button(ui, "BACK", Vector2(130, 596), Vector2(105, 76), Callable(self, "_set_move").bind("back", true), Callable(self, "_set_move").bind("back", false))
	_add_action_button(ui, "RIGHT", Vector2(246, 596), Vector2(105, 76), Callable(self, "_set_move").bind("right", true), Callable(self, "_set_move").bind("right", false))
	_add_action_button(ui, "FIRE", Vector2(1080, 548), Vector2(168, 112), Callable(self, "_set_fire").bind(true), Callable(self, "_set_fire").bind(false))
	_add_tap_button(ui, "FLASH", Vector2(1090, 448), Vector2(148, 76), _activate_flash)
	_add_tap_button(ui, "CYBER SHIELD", Vector2(910, 600), Vector2(160, 72), _activate_shield)
	_add_tap_button(ui, "RELOAD", Vector2(920, 510), Vector2(140, 72), _reload_weapon)
	_add_tap_button(ui, "NEXT GUN", Vector2(760, 600), Vector2(140, 72), _next_weapon)
	_add_tap_button(ui, "EMOTE 1", Vector2(760, 510), Vector2(140, 66), _emote_wave)
	_add_tap_button(ui, "EMOTE 2", Vector2(760, 438), Vector2(140, 66), _emote_guard)
	_add_tap_button(ui, "EMOTE 3", Vector2(760, 366), Vector2(140, 66), _emote_victory)
	rematch_button = _add_tap_button(ui, "REMATCH", Vector2(515, 350), Vector2(250, 92), _start_rematch)
	rematch_button.visible = false
	flash_overlay = ColorRect.new()
	flash_overlay.color = Color(1.0, 1.0, 1.0, 0.0)
	flash_overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	flash_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui.add_child(flash_overlay)

func _make_label(parent: Control, value: String, position: Vector2, dimensions: Vector2, font_size: int) -> Label:
	var label := Label.new()
	label.text = value
	label.position = position
	label.size = dimensions
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
	rematch_button.visible = false
	status_label.text = "NEW ROUND  •  SAME MAP"
	player.reset_for_rematch(Vector3(0.0, FLOOR_Y, 25.0))
	rival.reset_for_rematch(Vector3(0.0, FLOOR_Y, -25.0))
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
		weapon_label.text = str(PVPActor.WEAPONS[player.current_weapon]["name"])
	if ammo_label:
		ammo_label.text = "%d / %d  •  FLASH %d  •  SHIELD %s" % [
			player.ammunition, int(PVPActor.WEAPONS[player.current_weapon]["mag"]),
			player.flash_grenades, ("READY" if player.shield_cooldown <= 0.0 else "%.0fs" % player.shield_cooldown)
		]
	if score_label:
		score_label.text = "LOOMWILD  •  YOU %d  —  BOT %d  •  OFFLINE 1v1" % [player_score, rival_score]
