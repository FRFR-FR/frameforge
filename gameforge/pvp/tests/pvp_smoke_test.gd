extends SceneTree
const PVPActor = preload("res://scripts/pvp_actor.gd")

func _initialize() -> void:
	var match_scene := load("res://scenes/match.tscn") as PackedScene
	assert(match_scene != null, "Match scene must load")
	assert(ResourceLoader.exists("res://assets/map/GAMEFORGE_BlackTide_Port.glb"), "BLACKTIDE map must exist")
	assert(ResourceLoader.exists("res://assets/characters/Aster.glb"), "Aster operator must exist")
	assert(ResourceLoader.exists("res://assets/weapons/AegisAR.glb"), "Aegis AR must exist")
	assert(PVPActor.WEAPONS.size() == 10, "Exactly ten selectable guns must be available")

	var game := match_scene.instantiate() as PVPGame
	assert(game != null, "Match scene must instantiate as PVPGame")
	root.add_child(game)
	await process_frame
	await create_timer(1.5).timeout

	assert(is_instance_valid(game.player), "Player must spawn")
	assert(is_instance_valid(game.rival), "Bot rival must spawn")
	assert(is_instance_valid(game.rival_brain), "Autonomous bot controller must spawn")
	assert(game.get_nodes_in_group("pvp_fighters").size() == 2, "Offline match must contain exactly two fighters")
	assert(game.cover_positions.size() >= 20, "Combat map must expose enough tactical cover positions")

	var start := game.player.global_position
	game.player.set_move_input(Vector2(0.0, -1.0))
	await create_timer(0.8).timeout
	game.player.set_move_input(Vector2.ZERO)
	assert(game.player.global_position.distance_to(start) > 0.5, "Player must physically move through the map")

	var weapon_before := game.player.current_weapon
	game.player.cycle_weapon(1)
	assert(game.player.current_weapon != weapon_before, "Weapon cycling must work")

	var health_before := game.rival.health
	game.player.set_weapon(2)
	game.player.fire_at_position(game.rival.global_position + Vector3.UP * 1.15)
	await process_frame
	assert(game.rival.health < health_before or game.player.ammunition < int(PVPActor.WEAPONS[2]["mag"]), "Firing must consume ammunition or damage the rival")

	assert(game.player.request_roll(), "Player roll must be available on the ground")
	await create_timer(0.7).timeout
	assert(game.player.roll_seconds <= 0.0, "Roll must complete")

	assert(game.player.flash_grenades == 2, "Player must begin with two flash grenades")
	assert(game.player.activate_cyber_shield(), "Cyber shield must activate")
	assert(game.player.shield_seconds > 0.0, "Cyber shield must remain active")

	game.player.reset_for_rematch(game.player.global_position)
	assert(is_equal_approx(game.player.health, 100.0), "Rematch reset must restore player health")
	assert(game.player.flash_grenades == 2, "Rematch reset must restore grenades")

	print("PASS: BLACKTIDE offline match, physical movement, weapons, combat, roll, shield, bot and rematch gates.")
	quit(0)
