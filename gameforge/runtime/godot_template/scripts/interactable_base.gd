extends StaticBody3D
class_name GameForgeInteractable
@export var interaction_prompt := "Interact"
@export var interaction_event := ""
signal interacted(actor: Node3D)

func get_interaction_prompt() -> String:
    return interaction_prompt

func interact(actor: Node3D) -> void:
    interacted.emit(actor)
    if not interaction_event.is_empty():
        var quest_director := get_tree().get_first_node_in_group("quest_director")
        if quest_director and quest_director.has_method("report_event"):
            quest_director.report_event(interaction_event)
