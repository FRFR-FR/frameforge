extends SpringArm3D
class_name GameForgeThirdPersonCamera
@export var target: Node3D
@export var look_sensitivity: float = 0.0025
@export var min_pitch: float = deg_to_rad(-55.0)
@export var max_pitch: float = deg_to_rad(35.0)
@export var follow_smoothing: float = 12.0
var yaw := 0.0
var pitch := deg_to_rad(-12.0)
var look_enabled := true

func _ready() -> void:
    spring_length = 5.0
    if get_child_count() == 0:
        var camera := Camera3D.new()
        add_child(camera)
    Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_RIGHT:
        Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if event.pressed else Input.MOUSE_MODE_VISIBLE
    if event is InputEventMouseMotion and look_enabled and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
        yaw -= event.relative.x * look_sensitivity
        pitch = clampf(pitch - event.relative.y * look_sensitivity, min_pitch, max_pitch)

func _process(delta: float) -> void:
    if not is_instance_valid(target):
        return
    global_position = global_position.lerp(target.global_position + Vector3.UP * 1.4, 1.0 - exp(-follow_smoothing * delta))
    rotation = Vector3(pitch, yaw, 0.0)
