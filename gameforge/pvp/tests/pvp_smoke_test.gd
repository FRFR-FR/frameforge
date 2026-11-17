extends SceneTree

func _initialize() -> void:
	call_deferred("_run_test")

func _run_test() -> void:
	var packed := load("res://scenes/main.tscn") as PackedScene
	assert(packed != null, "Main PvP scene must load")
	var game := packed.instantiate() as PVPGame
	root.add_child(game)
	await process_frame
	await create_timer(2.5).timeout
	var fighters := get_nodes_in_group("pvp_fighters")
	assert(fighters.size() == 2, "The offline match must spawn exactly one player and one bot")
	assert(game.player != null and game.rival != null, "Both fighters must exist")
	assert(PVPActor.WEAPONS.size() == 10, "Exactly ten selectable guns must be available")
	for weapon_index in range(10):
		game.player.set_weapon(weapon_index)
		assert(game.player.current_weapon == weapon_index, "Every authored gun must be selectable")
	game.player.set_weapon(2)
	assert(game.rival.activate_cyber_shield(), "Bot cyber shield must activate")
	var rival_health_before_shield_test := game.rival.health
	game.rival.receive_damage(30.0, game.player.global_position)
	assert(is_equal_approx(game.rival.health, rival_health_before_shield_test), "Cyber shield must absorb incoming damage")
	assert(game.rival_brain != null, "The rival must have an autonomous AI controller")
	assert(game.rival_brain.state != "SCAN", "The bot must leave scan and make an autonomous decision")
	game._on_fighter_defeated(game.rival)
	assert(game.round_over, "A defeated bot must end the round")
	game._start_rematch()
	assert(not game.round_over, "Rematch must reset the round")
	assert(is_equal_approx(game.player.health, 100.0), "Rematch must restore player health")
	assert(game.player.flash_grenades == 2, "Rematch must restore the flash-grenade loadout")
	print("PASS: 1v1 offline match, autonomous bot, ten-gun loadout, defeat and rematch.")
	quit(0)
