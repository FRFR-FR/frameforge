extends Node
class_name GameForgeQuestDirector
signal quest_started(quest_id: String)
signal objective_updated(quest_id: String, objective_id: String, progress: int)
signal quest_completed(quest_id: String)
var quests: Dictionary = {}
var active_quest: String = ""
var flags: Dictionary = {}

func register_quest(definition: Dictionary) -> void:
    var quest_id := str(definition.get("id", ""))
    if quest_id.is_empty() or quests.has(quest_id):
        push_warning("Quest requires a unique non-empty id.")
        return
    var objectives: Array = []
    for source in definition.get("objectives", []):
        objectives.append({"id": str(source.get("id", "")), "target": maxi(1, int(source.get("target", 1))), "progress": 0, "event": str(source.get("event", ""))})
    quests[quest_id] = {"title": str(definition.get("title", quest_id)), "objectives": objectives, "status": "available"}

func start_quest(quest_id: String) -> bool:
    if not quests.has(quest_id) or quests[quest_id]["status"] != "available":
        return false
    quests[quest_id]["status"] = "active"
    active_quest = quest_id
    quest_started.emit(quest_id)
    return true

func report_event(event_name: String, amount: int = 1) -> void:
    if active_quest.is_empty():
        return
    var quest: Dictionary = quests[active_quest]
    for objective in quest["objectives"]:
        if objective["event"] == event_name and objective["progress"] < objective["target"]:
            objective["progress"] = mini(objective["target"], objective["progress"] + maxi(1, amount))
            objective_updated.emit(active_quest, objective["id"], objective["progress"])
    var done := true
    for objective in quest["objectives"]:
        done = done and objective["progress"] >= objective["target"]
    if done:
        quest["status"] = "completed"
        flags["quest_" + active_quest + "_complete"] = true
        quest_completed.emit(active_quest)
        active_quest = ""

func is_flag_set(flag_name: String) -> bool:
    return bool(flags.get(flag_name, false))
