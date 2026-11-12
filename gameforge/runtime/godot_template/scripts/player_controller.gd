extends CharacterBody3D
class_name GameForgePlayerController
## Responsive third-person movement with camera-relative direction and explicit input lock.
@export var walk_speed: float = 4.5
@export var sprint_speed: float = 7.0
@export var acceleration: float = 18.0
@export var deceleration: float = 22.0
@export var jump_velocity: float = 4.8
@export var gravity: float = 9.8
@export var camera_pivot: Node3D
@export var turn_speed: float = 12.0
var input_enabled := true

func _physics_process(delta: float) -> void:
    if not is_on_floor():
        velocity.y -= gravity * delta
    elif input_enabled and Input.is_action_just_pressed("jump"):
        velocity.y = jump_velocity

    var input_vector := Vector2.ZERO
    if input_enabled:
        input_vector = Input.get_vector("move_left", "move_right", "move_forward", "move_back")

    var basis := global_basis
    var active_camera := get_viewport().get_camera_3d()
    if active_camera:
        basis = active_camera.global_basis
    elif camera_pivot:
        basis = camera_pivot.global_basis
    var direction := basis * Vector3(input_vector.x, 0.0, input_vector.y)
    direction.y = 0.0
    direction = direction.normalized()

    var sprinting := input_enabled and Input.is_action_pressed("sprint")
    var speed := sprint_speed if sprinting else walk_speed
    var target := direction * speed
    var rate := acceleration if direction.length_squared() > 0.001 else deceleration
    velocity.x = move_toward(velocity.x, target.x, rate * delta)
    velocity.z = move_toward(velocity.z, target.z, rate * delta)

    if direction.length_squared() > 0.001:
        var target_yaw := atan2(-direction.x, -direction.z)
        rotation.y = lerp_angle(rotation.y, target_yaw, 1.0 - exp(-turn_speed * delta))
    move_and_slide()

func set_gameplay_input_enabled(enabled: bool) -> void:
    input_enabled = enabled
