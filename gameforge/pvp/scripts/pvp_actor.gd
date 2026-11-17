extends CharacterBody3D
class_name PVPActor

signal defeated(actor: PVPActor)
signal health_changed(actor: PVPActor, current: float, maximum: float)
signal weapon_changed(actor: PVPActor, weapon_name: String)

const WEAPONS := [
	{"id":"Vesper9","name":"Vesper-9","damage":25.0,"rpm":390.0,"mag":16,"reload":1.25,"range":42.0,"spread":0.012,"pellets":1},
	{"id":"FluxSMG","name":"Flux SMG","damage":13.0,"rpm":900.0,"mag":34,"reload":1.55,"range":34.0,"spread":0.038,"pellets":1},
	{"id":"AegisAR","name":"Aegis AR","damage":19.0,"rpm":720.0,"mag":30,"reload":1.7,"range":58.0,"spread":0.018,"pellets":1},
	{"id":"KestrelBurst","name":"Kestrel Burst","damage":17.0,"rpm":780.0,"mag":27,"reload":1.65,"range":54.0,"spread":0.022,"pellets":1},
	{"id":"RangerDMR","name":"Ranger DMR","damage":36.0,"rpm":300.0,"mag":15,"reload":1.9,"range":78.0,"spread":0.006,"pellets":1},
	{"id":"Longbow","name":"Longbow","damage":88.0,"rpm":62.0,"mag":5,"reload":2.45,"range":110.0,"spread":0.002,"pellets":1},
	{"id":"Breach12","name":"Breach-12","damage":10.5,"rpm":96.0,"mag":8,"reload":2.0,"range":22.0,"spread":0.075,"pellets":8},
	{"id":"BastionLMG","name":"Bastion LMG","damage":16.0,"rpm":660.0,"mag":62,"reload":2.7,"range":62.0,"spread":0.032,"pellets":1},
	{"id":"PulseCarbine","name":"Pulse Carbine","damage":22.0,"rpm":510.0,"mag":26,"reload":1.7,"range":66.0,"spread":0.014,"pellets":1},
	{"id":"ArcLance","name":"Arc Lance","damage":70.0,"rpm":145.0,"mag":6,"reload":2.25,"range":86.0,"spread":0.004,"pellets":1}
]
const CHARACTER_IDS := ["Aster", "Bront", "Koro", "Luma", "Miri", "Nyx", "Orin", "Pika", "Sola", "Vey"]

@export var is_player := false
@export var character_id := "Aster"
var game_root: Node
var move_input := Vector2.ZERO
var ai_direction := Vector3.ZERO
var health := 100.0
var maximum_health := 100.0
var shield_energy := 0.0
var shield_seconds := 0.0
var shield_cooldown := 0.0
var flash_seconds := 0.0
var flash_grenades := 2
var reload_seconds := 0.0
var fire_cooldown := 0.0
var current_weapon := 2
var ammunition := 30
var defeated_state := false
var last_hit_time := -100.0
var camera_yaw := 0.0
var camera_pitch := -0.16
var camera_pivot: Node3D
var camera_arm: SpringArm3D
var camera: Camera3D
var weapon_mount: Node3D
var weapon_visual: Node3D
var character_visual: Node3D
var shield_visual: MeshInstance3D
var running := false

func _ready() -> void:
	add_to_group("pvp_fighters")
	collision_layer = 1
	collision_mask = 1
	floor_snap_length = 0.25
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.37
	capsule.height = 1.82
	var collision := CollisionShape3D.new()
	collision.shape = capsule
	collision.position.y = 0.91
	add_child(collision)
	_load_character()
	_create_weapon_mount()
	_create_shield_visual()
	if is_player:
		_create_camera()
	health_changed.emit(self, health, maximum_health)
	set_weapon(current_weapon)
	_play_idle()

func _physics_process(delta: float) -> void:
	if defeated_state:
		velocity = Vector3.ZERO
		return
	fire_cooldown = maxf(0.0, fire_cooldown - delta)
	shield_cooldown = maxf(0.0, shield_cooldown - delta)
	flash_seconds = maxf(0.0, flash_seconds - delta)
	if shield_seconds > 0.0:
		shield_seconds = maxf(0.0, shield_seconds - delta)
		if shield_seconds <= 0.0 or shield_energy <= 0.0:
			_set_shield_visible(false)
	if reload_seconds > 0.0:
		reload_seconds = maxf(0.0, reload_seconds - delta)
		if reload_seconds <= 0.0:
			ammunition = int(WEAPONS[current_weapon]["mag"])
	if not is_on_floor():
		velocity.y -= 19.0 * delta
	else:
		velocity.y = -0.5
	var direction := Vector3.ZERO
	if is_player:
		direction = Vector3(move_input.x, 0.0, move_input.y).rotated(Vector3.UP, camera_yaw)
	else:
		direction = ai_direction
	direction.y = 0.0
	direction = direction.normalized()
	running = direction.length_squared() > 0.45
	var speed := 5.9 if running else 4.1
	if not is_player:
		speed = 5.3 if running else 3.8
	velocity.x = move_toward(velocity.x, direction.x * speed, delta * (18.0 if running else 14.0))
	velocity.z = move_toward(velocity.z, direction.z * speed, delta * (18.0 if running else 14.0))
	if is_player:
		rotation.y = camera_yaw
	elif direction.length_squared() > 0.002:
		rotation.y = atan2(-direction.x, -direction.z)
	move_and_slide()

func _load_character() -> void:
	var path := "res://assets/characters/%s.glb" % character_id
	if ResourceLoader.exists(path):
		var packed := load(path) as PackedScene
		if packed:
			character_visual = packed.instantiate()
			character_visual.name = "RiggedCharacter_" + character_id
			character_visual.scale = Vector3.ONE * 0.56
			add_child(character_visual)
			return
	_add_fallback_body()

func _add_fallback_body() -> void:
	var mesh := MeshInstance3D.new()
	var capsule := CapsuleMesh.new()
	capsule.radius = 0.36
	capsule.height = 1.78
	mesh.mesh = capsule
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.12, 0.7, 0.86) if is_player else Color(0.92, 0.38, 0.19)
	mat.metallic = 0.28
	mat.roughness = 0.34
	mesh.material_override = mat
	mesh.position.y = 0.9
	add_child(mesh)
	character_visual = mesh

func _create_weapon_mount() -> void:
	weapon_mount = Node3D.new()
	weapon_mount.name = "WeaponMount"
	weapon_mount.position = Vector3(0.37, 1.16, -0.25)
	weapon_mount.rotation.y = PI * 0.5
	add_child(weapon_mount)

func _create_camera() -> void:
	camera_pivot = Node3D.new()
	camera_pivot.name = "CameraPivot"
	camera_pivot.position = Vector3(0.0, 1.43, 0.0)
	add_child(camera_pivot)
	camera_arm = SpringArm3D.new()
	camera_arm.name = "ThirdPersonCameraArm"
	camera_arm.spring_length = 5.0
	camera_arm.margin = 0.18
	camera_arm.rotation.x = camera_pitch
	camera_pivot.add_child(camera_arm)
	camera = Camera3D.new()
	camera.name = "PlayerCamera"
	camera.current = true
	camera.fov = 76.0
	camera_arm.add_child(camera)
	camera_pivot.rotation.y = camera_yaw

func apply_look_delta(delta: Vector2) -> void:
	camera_yaw -= delta.x * 0.0042
	camera_pitch = clampf(camera_pitch - delta.y * 0.0032, -0.78, 0.28)
	if camera_pivot:
		camera_pivot.rotation.y = camera_yaw
		camera_arm.rotation.x = camera_pitch

func get_aim_point(distance: float = 100.0) -> Vector3:
	if camera:
		return camera.global_position + (-camera.global_basis.z) * distance
	return global_position + Vector3(0.0, 1.3, -distance)

func set_move_input(value: Vector2) -> void:
	move_input = value.limit_length(1.0)

func set_ai_direction(value: Vector3) -> void:
	ai_direction = value.limit_length(1.0)

func set_weapon(index: int) -> void:
	current_weapon = posmod(index, WEAPONS.size())
	var weapon: Dictionary = WEAPONS[current_weapon]
	ammunition = int(weapon["mag"])
	reload_seconds = 0.0
	if is_instance_valid(weapon_visual):
		weapon_visual.queue_free()
	weapon_visual = null
	var path := "res://assets/weapons/%s.glb" % weapon["id"]
	if ResourceLoader.exists(path):
		var packed := load(path) as PackedScene
		if packed:
			weapon_visual = packed.instantiate()
			weapon_visual.scale = Vector3.ONE * 0.48
			weapon_visual.position = Vector3(0.0, 0.0, -0.08)
			weapon_mount.add_child(weapon_visual)
	if weapon_visual == null:
		var fallback := MeshInstance3D.new()
		var box := BoxMesh.new()
		box.size = Vector3(0.8, 0.13, 0.18)
		fallback.mesh = box
		weapon_mount.add_child(fallback)
		weapon_visual = fallback
	weapon_changed.emit(self, str(weapon["name"]))

func cycle_weapon() -> void:
	set_weapon(current_weapon + 1)

func reload_weapon() -> void:
	if defeated_state or reload_seconds > 0.0:
		return
	var magazine := int(WEAPONS[current_weapon]["mag"])
	if ammunition >= magazine:
		return
	reload_seconds = float(WEAPONS[current_weapon]["reload"])

func fire_at_position(target_point: Vector3) -> bool:
	if defeated_state or flash_seconds > 0.0 or fire_cooldown > 0.0 or reload_seconds > 0.0:
		return false
	if ammunition <= 0:
		reload_weapon()
		return false
	var weapon: Dictionary = WEAPONS[current_weapon]
	ammunition -= 1
	fire_cooldown = 60.0 / float(weapon["rpm"])
	var origin := global_position + Vector3.UP * 1.32
	var direction := (target_point - origin).normalized()
	var space := get_world_3d().direct_space_state
	var pellets := int(weapon["pellets"])
	for pellet in pellets:
		var noisy := (direction
			+ global_basis.x * randf_range(-float(weapon["spread"]), float(weapon["spread"]))
			+ Vector3.UP * randf_range(-float(weapon["spread"]), float(weapon["spread"]))).normalized()
		var query := PhysicsRayQueryParameters3D.create(origin, origin + noisy * float(weapon["range"]))
		query.exclude = [get_rid()]
		query.collision_mask = 1
		var hit := space.intersect_ray(query)
		if not hit.is_empty():
			var target = hit.get("collider")
			if target is PVPActor:
				(target as PVPActor).receive_damage(float(weapon["damage"]), global_position)
	if game_root and game_root.has_method("show_shot_effect"):
		game_root.show_shot_effect(origin, origin + direction * minf(14.0, float(weapon["range"])))
	return true

func receive_damage(amount: float, attacker_position: Vector3) -> void:
	if defeated_state or amount <= 0.0:
		return
	last_hit_time = Time.get_ticks_msec() / 1000.0
	var remaining := amount
	if shield_seconds > 0.0 and shield_energy > 0.0:
		var absorbed := minf(shield_energy, remaining)
		shield_energy -= absorbed
		remaining -= absorbed
		if shield_energy <= 0.0:
			shield_seconds = 0.0
			_set_shield_visible(false)
	if remaining > 0.0:
		health = maxf(0.0, health - remaining)
	health_changed.emit(self, health, maximum_health)
	if health <= 0.0:
		defeated_state = true
		defeated.emit(self)

func activate_cyber_shield() -> bool:
	if defeated_state or shield_cooldown > 0.0 or shield_seconds > 0.0:
		return false
	shield_energy = 110.0
	shield_seconds = 5.0
	shield_cooldown = 13.0
	_set_shield_visible(true)
	return true

func _create_shield_visual() -> void:
	shield_visual = MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 1.03
	sphere.height = 2.06
	shield_visual.mesh = sphere
	shield_visual.position.y = 0.95
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.albedo_color = Color(0.12, 0.72, 1.0, 0.22)
	material.emission_enabled = true
	material.emission = Color(0.08, 0.6, 1.0)
	material.emission_energy_multiplier = 1.6
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	shield_visual.material_override = material
	shield_visual.visible = false
	add_child(shield_visual)

func _set_shield_visible(value: bool) -> void:
	if is_instance_valid(shield_visual):
		shield_visual.visible = value

func throw_flash_grenade(target_point: Vector3) -> bool:
	if defeated_state or flash_grenades <= 0 or not game_root or not game_root.has_method("throw_flash_grenade"):
		return false
	flash_grenades -= 1
	game_root.throw_flash_grenade(self, target_point)
	return true

func apply_flash(duration: float) -> void:
	flash_seconds = maxf(flash_seconds, duration)
	if is_player and game_root and game_root.has_method("show_flash_overlay"):
		game_root.show_flash_overlay(duration)

func play_emote(keyword: String) -> bool:
	if not character_visual:
		return false
	for item in character_visual.find_children("*", "AnimationPlayer", true, false):
		var player := item as AnimationPlayer
		for animation_name in player.get_animation_list():
			if keyword.to_lower() in animation_name.to_lower():
				player.play(animation_name)
				return true
	return false

func _play_idle() -> void:
	if character_visual:
		play_emote("idle")

func reset_for_rematch(spawn_position: Vector3) -> void:
	global_position = spawn_position
	velocity = Vector3.ZERO
	move_input = Vector2.ZERO
	ai_direction = Vector3.ZERO
	health = maximum_health
	shield_energy = 0.0
	shield_seconds = 0.0
	shield_cooldown = 0.0
	flash_seconds = 0.0
	flash_grenades = 2
	reload_seconds = 0.0
	fire_cooldown = 0.0
	defeated_state = false
	ammunition = int(WEAPONS[current_weapon]["mag"])
	_set_shield_visible(false)
	health_changed.emit(self, health, maximum_health)
	_play_idle()
