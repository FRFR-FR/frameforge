extends CharacterBody3D
class_name GameForgeNPCBrain
enum State { IDLE, PATROL, CHASE, RETURN }
@export var move_speed := 2.8
@export var detection_range := 10.0
@export var attack_range := 1.8
@export var player_path: NodePath
@export var patrol_points: Array[Node3D] = []
var state := State.IDLE
var patrol_index := 0
var home_position: Vector3
var gravity := 9.8

func _ready() -> void:
    home_position = global_position

func _physics_process(delta: float) -> void:
    var player := get_node_or_null(player_path) as Node3D
    if not is_on_floor():
        velocity.y -= gravity * delta
    if player and global_position.distance_to(player.global_position) <= detection_range:
        state = State.CHASE
    elif state == State.CHASE:
        state = State.RETURN
    match state:
        State.IDLE:
            velocity.x = move_toward(velocity.x, 0.0, move_speed * delta)
            velocity.z = move_toward(velocity.z, 0.0, move_speed * delta)
            if not patrol_points.is_empty():
                state = State.PATROL
        State.PATROL:
            if patrol_points.is_empty():
                state = State.IDLE
            else:
                _move_toward_point(patrol_points[patrol_index].global_position, delta)
                if global_position.distance_to(patrol_points[patrol_index].global_position) < 0.5:
                    patrol_index = (patrol_index + 1) % patrol_points.size()
        State.CHASE:
            if player:
                _move_toward_point(player.global_position, delta)
                if global_position.distance_to(player.global_position) <= attack_range:
                    velocity.x = 0.0
                    velocity.z = 0.0
        State.RETURN:
            _move_toward_point(home_position, delta)
            if global_position.distance_to(home_position) < 0.5:
                state = State.PATROL if not patrol_points.is_empty() else State.IDLE
    move_and_slide()

func _move_toward_point(point: Vector3, delta: float) -> void:
    var direction := point - global_position
    direction.y = 0.0
    direction = direction.normalized()
    velocity.x = move_toward(velocity.x, direction.x * move_speed, move_speed * 4.0 * delta)
    velocity.z = move_toward(velocity.z, direction.z * move_speed, move_speed * 4.0 * delta)
    if direction.length_squared() > 0.01:
        look_at(global_position + direction, Vector3.UP)
