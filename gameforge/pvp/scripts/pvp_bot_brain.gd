extends Node
class_name PVPBotBrain

@export var actor: PVPActor
@export var target: PVPActor
@export var game_root: Node
var think_left := 0.0
var strafe_sign := 1.0
var strafe_left := 0.0
var cover_position := Vector3.ZERO
var state := "SCAN"
var grenade_cooldown := 0.0
var last_weapon := -1

func _physics_process(delta: float) -> void:
	if not is_instance_valid(actor) or not is_instance_valid(target):
		return
	if actor.defeated_state or target.defeated_state:
		actor.set_ai_direction(Vector3.ZERO)
		return
	think_left -= delta
	strafe_left -= delta
	grenade_cooldown = maxf(0.0, grenade_cooldown - delta)
	if think_left > 0.0:
		return
	think_left = 0.16
	if strafe_left <= 0.0:
		strafe_sign *= -1.0
		strafe_left = randf_range(1.0, 2.0)
	var gap := actor.global_position.distance_to(target.global_position)
	var visible := _has_line_of_sight()
	if actor.flash_seconds > 0.0:
		state = "FLASHED"
		actor.set_ai_direction(Vector3.ZERO)
		return
	if actor.health < 46.0 and (cover_position == Vector3.ZERO or actor.global_position.distance_to(cover_position) < 1.8):
		cover_position = _choose_cover()
	if actor.health < 52.0 and cover_position != Vector3.ZERO:
		var retreat := cover_position - actor.global_position
		retreat.y = 0.0
		if retreat.length() > 1.8:
			state = "HIDE"
			actor.set_ai_direction(retreat.normalized())
			if actor.shield_seconds <= 0.0 and actor.shield_cooldown <= 0.0:
				actor.activate_cyber_shield()
			if gap < 8.5 and grenade_cooldown <= 0.0:
				_throw_flash()
			return
		state = "DEFEND"
		actor.set_ai_direction(Vector3.ZERO)
		if actor.shield_seconds <= 0.0 and actor.shield_cooldown <= 0.0:
			actor.activate_cyber_shield()
		if visible and gap < 52.0:
			actor.fire_at_position(target.global_position + Vector3.UP * 1.15)
		return
	cover_position = Vector3.ZERO
	_select_weapon(gap)
	var toward := target.global_position - actor.global_position
	toward.y = 0.0
	var forward := toward.normalized()
	var movement := Vector3.ZERO
	if gap > 30.0:
		state = "RUN_TO_ENGAGE"
		movement = forward
	elif not visible:
		state = "FLANK"
		movement = (forward + Vector3(-forward.z, 0.0, forward.x) * 0.45 * strafe_sign).normalized()
	elif gap < 9.0:
		state = "STRAFE_AND_DEFEND"
		movement = Vector3(-forward.z, 0.0, forward.x) * strafe_sign
		if actor.shield_seconds <= 0.0 and actor.shield_cooldown <= 0.0 and actor.health < 72.0:
			actor.activate_cyber_shield()
	else:
		state = "ATTACK"
		if gap > 19.0:
			movement = forward * 0.28
		else:
			movement = Vector3(-forward.z, 0.0, forward.x) * strafe_sign * 0.38
	actor.set_ai_direction(movement.normalized())
	if visible and gap <= float(PVPActor.WEAPONS[actor.current_weapon]["range"]) * 0.92:
		actor.fire_at_position(target.global_position + Vector3.UP * randf_range(1.0, 1.38))
	if gap < 10.0 and visible and grenade_cooldown <= 0.0:
		_throw_flash()
	if actor.ammunition <= 2 and actor.reload_seconds <= 0.0:
		actor.reload_weapon()
	if actor.health < 68.0 and actor.shield_seconds <= 0.0 and actor.shield_cooldown <= 0.0 and not visible:
		actor.activate_cyber_shield()

func _select_weapon(distance: float) -> void:
	var desired := 2
	if distance < 9.0:
		desired = 6
	elif distance < 19.0:
		desired = 1
	elif distance > 58.0:
		desired = 5
	elif distance > 36.0:
		desired = 4
	if desired != last_weapon:
		actor.set_weapon(desired)
		last_weapon = desired

func _has_line_of_sight() -> bool:
	var origin := actor.global_position + Vector3.UP * 1.3
	var destination := target.global_position + Vector3.UP * 1.15
	var query := PhysicsRayQueryParameters3D.create(origin, destination)
	query.exclude = [actor.get_rid()]
	query.collision_mask = 1
	var result := actor.get_world_3d().direct_space_state.intersect_ray(query)
	return result.is_empty() or result.get("collider") == target

func _choose_cover() -> Vector3:
	if not game_root or not game_root.has_method("get_cover_positions"):
		return actor.global_position - (target.global_position - actor.global_position).normalized() * 7.0
	var candidates: Array = game_root.get_cover_positions()
	if candidates.is_empty():
		return actor.global_position - (target.global_position - actor.global_position).normalized() * 7.0
	var best: Vector3 = candidates[0]
	var best_score := INF
	for point in candidates:
		var p: Vector3 = point
		var to_bot := actor.global_position.distance_to(p)
		var from_player := target.global_position.distance_to(p)
		var score := to_bot + maxf(0.0, 10.0 - from_player) * 2.0
		if score < best_score:
			best_score = score
			best = p
	return best

func _throw_flash() -> void:
	if actor.throw_flash_grenade(target.global_position + Vector3.UP * 0.6):
		grenade_cooldown = 12.0
