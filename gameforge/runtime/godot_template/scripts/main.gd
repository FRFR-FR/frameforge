extends Node3D

const PlayerController = preload("res://scripts/player_controller.gd")
const WorldGenerator = preload("res://scripts/world_generator.gd")
const CameraRig = preload("res://scripts/third_person_camera.gd")
const QualityManager = preload("res://scripts/quality_manager.gd")
const QuestDirector = preload("res://scripts/quest_director.gd")

func _ready() -> void:
    _configure_input()
    _create_environment()
    _create_world()
    _create_player()
    add_child(QualityManager.new())
    var quests := QuestDirector.new()
    quests.name = "QuestDirector"
    add_child(quests)

func _configure_input() -> void:
    _bind_key("move_forward", KEY_W)
    _bind_key("move_back", KEY_S)
    _bind_key("move_left", KEY_A)
    _bind_key("move_right", KEY_D)
    _bind_key("jump", KEY_SPACE)
    _bind_key("sprint", KEY_SHIFT)
    _bind_key("interact", KEY_E)

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

func _create_world() -> void:
    var world := Node3D.new()
    world.name = "GeneratedWorld"
    world.set_script(WorldGenerator)
    world.world_seed = 42017
    world.grid_size = 18
    add_child(world)

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
    var camera_arm := SpringArm3D.new()
    camera_arm.name = "ThirdPersonCamera"
    camera_arm.set_script(CameraRig)
    camera_arm.target = player
    camera_pivot.add_child(camera_arm)
    player.set("camera_pivot", camera_pivot)
    add_child(player)
