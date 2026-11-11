extends Node3D
class_name GameForgeWorldGenerator
## Seeded low-poly world blockout generator. Art assets can replace generated meshes later.
@export var world_seed: int = 42017
@export_range(4, 64, 1) var grid_size: int = 18
@export var cell_size: float = 4.0
@export var obstacle_density: float = 0.12
@export var landmark_every: int = 6
var rng := RandomNumberGenerator.new()

func _ready() -> void:
    rng.seed = world_seed
    _build_ground()
    _build_obstacles()
    _build_landmarks()

func _build_ground() -> void:
    var body := StaticBody3D.new()
    body.name = "GeneratedGround"
    var mesh_instance := MeshInstance3D.new()
    var mesh := PlaneMesh.new()
    mesh.size = Vector2(grid_size * cell_size, grid_size * cell_size)
    mesh_instance.mesh = mesh
    var material := StandardMaterial3D.new()
    material.albedo_color = Color(0.10, 0.16, 0.14)
    material.roughness = 1.0
    mesh_instance.material_override = material
    body.add_child(mesh_instance)
    var collision := CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = Vector3(grid_size * cell_size, 0.2, grid_size * cell_size)
    collision.shape = shape
    collision.position.y = -0.1
    body.add_child(collision)
    add_child(body)

func _build_obstacles() -> void:
    var half := grid_size / 2
    for x in range(-half, half):
        for z in range(-half, half):
            if rng.randf() > obstacle_density or Vector2(x, z).length() < 3.0:
                continue
            var height := rng.randf_range(0.8, 3.2)
            var block := StaticBody3D.new()
            block.position = Vector3(x * cell_size, height * 0.5, z * cell_size)
            var mesh_instance := MeshInstance3D.new()
            var box := BoxMesh.new()
            box.size = Vector3(rng.randf_range(1.0, 2.4), height, rng.randf_range(1.0, 2.4))
            mesh_instance.mesh = box
            var material := StandardMaterial3D.new()
            material.albedo_color = Color.from_hsv(rng.randf_range(0.30, 0.48), 0.28, rng.randf_range(0.25, 0.48))
            material.roughness = 0.92
            mesh_instance.material_override = material
            block.add_child(mesh_instance)
            var collision := CollisionShape3D.new()
            var shape := BoxShape3D.new()
            shape.size = box.size
            collision.shape = shape
            block.add_child(collision)
            add_child(block)

func _build_landmarks() -> void:
    for x in range(-grid_size / 2, grid_size / 2, landmark_every):
        for z in range(-grid_size / 2, grid_size / 2, landmark_every):
            var pillar := MeshInstance3D.new()
            var mesh := CylinderMesh.new()
            mesh.top_radius = 0.35
            mesh.bottom_radius = 0.6
            mesh.height = 3.8
            pillar.mesh = mesh
            pillar.position = Vector3(x * cell_size, 1.9, z * cell_size)
            var material := StandardMaterial3D.new()
            material.albedo_color = Color(0.36, 0.28, 0.22)
            pillar.material_override = material
            add_child(pillar)
