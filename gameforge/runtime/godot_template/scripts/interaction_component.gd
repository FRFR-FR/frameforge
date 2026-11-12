extends Node
class_name GameForgeInteraction
signal interaction_found(target: Node)
signal interaction_lost
@export var actor: Node3D
@export var reach: float = 2.8
@export var collision_mask: int = 1
var current_target: Node3D

func _physics_process(_delta: float) -> void:
    if not is_instance_valid(actor):
        return
    var camera := actor.get_viewport().get_camera_3d()
    if camera == null:
        return
    var origin := camera.global_position
    var query := PhysicsRayQueryParameters3D.create(origin, origin - camera.global_basis.z * reach, collision_mask)
    query.exclude = [actor.get_rid()]
    var hit := actor.get_world_3d().direct_space_state.intersect_ray(query)
    var found: Node3D = hit.get("collider") as Node3D if hit else null
    if found != current_target:
        current_target = found
        if is_instance_valid(found):
            interaction_found.emit(found)
        else:
            interaction_lost.emit()
    if current_target and Input.is_action_just_pressed("interact") and current_target.has_method("interact"):
        current_target.interact(actor)

func get_prompt() -> String:
    if is_instance_valid(current_target) and current_target.has_method("get_interaction_prompt"):
        return str(current_target.get_interaction_prompt())
    return ""
