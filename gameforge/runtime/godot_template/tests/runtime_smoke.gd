extends SceneTree
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
    assert(root_node.get_node_or_null("DialogueDirector") != null, "Dialogue director must exist")
    assert(root_node.get_node_or_null("SaveManager") != null, "Save manager must exist")
    assert(root_node.get_node_or_null("AccessibilitySettings") != null, "Accessibility settings must exist")

    var inventory_script = load("res://scripts/inventory_component.gd")
    var inventory = inventory_script.new()
    assert(inventory.add_item("key", 2), "Inventory should accept items")
    assert(inventory.count("key") == 2, "Inventory count should update")
    assert(inventory.remove_item("key"), "Inventory should remove items")
    assert(inventory.count("key") == 1, "Inventory count should decrement")

    var quest_script = load("res://scripts/quest_director.gd")
    var quest = quest_script.new()
    quest.register_quest({"id":"test","objectives":[{"id":"find","target":1,"event":"found"}]})
    assert(quest.start_quest("test"), "Quest should start")
    quest.report_event("found")
    assert(quest.is_flag_set("quest_test_complete"), "Quest completion should persist a flag")

    var dialogue_script = load("res://scripts/dialogue_director.gd")
    var dialogue = dialogue_script.new()
    assert(dialogue.register_dialogue({"id":"test","lines":[{"speaker":"A","text":"Hello"}]}), "Dialogue should register")
    assert(dialogue.start("test"), "Dialogue should start")
    dialogue.continue_dialogue()
    assert(dialogue.active_id.is_empty(), "Dialogue should finish after the final line is continued")

    root_node.queue_free()
    print("GAMEFORGE runtime smoke tests passed.")
    quit(0)
