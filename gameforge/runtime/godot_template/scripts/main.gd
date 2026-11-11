extends Node3D

## First playable runtime smoke scene: a lit test arena and third-person
## capsule controller. Generated projects replace the capsule with their
## authored character while retaining the controller contract.

const PlayerController = preload("res://scripts/player_controller.gd")

func _ready() -> void:
    _configure_input()
    _create_environment()
    _create_ground()
    _create_player()

func _configure_input() -> void:
    _bind_key("move_forward", KEY_W)
    _bind_key("move_back", KEY_S)
    _bind_key("move_left", KEY_A)
    _bind_key("move_right", KEY_D)
    _bind_key("jump", KEY_SPACE)
    _bind_key("sprint", KEY_SHIFT)

func _bind_key(action: StringName, key: Key) -> void:
    if not InputMap.has_action(action):
        InputMap.add_action(action)
    var event := InputEventKey.new()
    event.physical_keycode = key
    InputMap.action_add_event(action, event)

func _create_environment() -> void:
    var environment_node := WorldEnvironment.new()
    var environment_resource := Environment.new()
    environment_resource.background_mode = Environment.BG_SKY
    environment_resource.sky = Sky.new()
    environment_resource.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    environment_resource.ambient_light_color = Color(0.42, 0.48, 0.62)
    environment_resource.ambient_light_energy = 0.65
    environment_node.environment = environment_resource
    add_child(environment_node)

    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-48.0, -28.0, 0.0)
    sun.light_energy = 1.1
    add_child(sun)

func _create_ground() -> void:
    var ground := StaticBody3D.new()
    ground.name = "Ground"

    var mesh_instance := MeshInstance3D.new()
    var mesh := PlaneMesh.new()
    mesh.size = Vector2(40.0, 40.0)
    mesh_instance.mesh = mesh
    var material := StandardMaterial3D.new()
    material.albedo_color = Color(0.12, 0.19, 0.17)
    material.roughness = 0.95
    mesh_instance.material_override = material
    ground.add_child(mesh_instance)

    var collision := CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = Vector3(40.0, 0.2, 40.0)
    collision.shape = shape
    collision.position.y = -0.1
    ground.add_child(collision)
    add_child(ground)

func _create_player() -> void:
    var player := CharacterBody3D.new()
    player.name = "Player"
    player.position = Vector3(0.0, 1.1, 4.0)
    player.set_script(PlayerController)

    var body_shape := CollisionShape3D.new()
    var capsule := CapsuleShape3D.new()
    capsule.radius = 0.38
    capsule.height = 1.8
    body_shape.shape = capsule
    player.add_child(body_shape)

    var body_mesh := MeshInstance3D.new()
    var capsule_mesh := CapsuleMesh.new()
    capsule_mesh.radius = 0.38
    capsule_mesh.height = 1.8
    body_mesh.mesh = capsule_mesh
    var body_material := StandardMaterial3D.new()
    body_material.albedo_color = Color(0.28, 0.62, 0.82)
    body_material.roughness = 0.65
    body_mesh.material_override = body_material
    player.add_child(body_mesh)

    var camera_pivot := Node3D.new()
    camera_pivot.name = "CameraPivot"
    camera_pivot.position = Vector3(0.0, 1.35, 0.0)
    player.add_child(camera_pivot)

    var camera := Camera3D.new()
    camera.position = Vector3(0.0, 2.0, 6.0)
    camera.look_at_from_position(camera.position, Vector3.ZERO)
    camera_pivot.add_child(camera)
    player.set("camera_pivot", camera_pivot)

    add_child(player)
