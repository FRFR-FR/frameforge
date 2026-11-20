extends SceneTree
const PVPActor = preload("res://scripts/pvp_actor.gd")

func _initialize() -> void:
	var main_scene := load("res://scenes/main.tscn") as PackedScene
	assert(main_scene != null, "Main PvP scene must load")
	assert(ResourceLoader.exists("res://assets/map/GAMEFORGE_BlackTide_Port.glb"), "BLACKTIDE map must exist")
	assert(ResourceLoader.exists("res://assets/characters/Aster.glb"), "Aster operator must exist")
	assert(ResourceLoader.exists("res://assets/weapons/AegisAR.glb"), "Aegis AR must exist")
	assert(PVPActor.WEAPONS.size() == 10, "Exactly ten selectable guns must be available")
	print("PASS: project scene, authored map, rigged operator and ten-gun loadout are present.")
	quit(0)
