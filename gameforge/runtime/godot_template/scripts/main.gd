extends Node3D

## Minimal boot scene used to verify generated Godot projects.
## Production projects replace this scene with the generated vertical slice.

func _ready() -> void:
    _create_environment()
    _create_ground()

func _create_environment() -> void:
    var environment := WorldEnvironment.new()
    var resource := Environment.new()
    resource.background_mode = Environment.BG_SKY
    resource.sky = Sky.new()
    resource.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    resource.ambient_light_color = Color(0.42, 0.48, 0.62)
    resource.ambient_light_energy = 0.65
    environment.environment = resource
    add_child(environment)

    var light := DirectionalLight3D.new()
    light.rotation_degrees = Vector3(-48.0, -28.0, 0.0)
    light.light_energy = 1.1
    add_child(light)

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
