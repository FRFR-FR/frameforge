extends SceneTree
## Headless smoke test for runtime systems and generated world.
func _initialize() -> void:
    call_deferred("_run")

func _run() -> void:
    var main_scene = load("res://scenes/main.tscn")
    assert(main_scene != null, "Main scene must load")
    var root_node = main_scene.instantiate()
    get_root().add_child(root_node)
    await process_frame
    assert(root_node.get_node_or_null("GeneratedWorld") != null, "Procedural world must exist")
    assert(root_node.get_node_or_null("Player") != null, "Player must exist")
    assert(root_node.get_node_or_null("QuestDirector") != null, "Quest director must exist")
    var player = root_node.get_node("Player")
    assert(player is CharacterBody3D, "Player must be a CharacterBody3D")
    root_node.queue_free()
    print("GAMEFORGE runtime smoke tests passed.")
    quit(0)
