extends Node
class_name GameForgeDialogueDirector
signal line_started(line: Dictionary)
signal dialogue_finished(dialogue_id: String)
signal choice_requested(options: Array)
var dialogues: Dictionary = {}
var active_id := ""
var cursor := 0
var waiting_for_choice := false

func register_dialogue(data: Dictionary) -> bool:
    var dialogue_id := str(data.get("id", ""))
    var lines: Array = data.get("lines", [])
    if dialogue_id.is_empty() or lines.is_empty():
        return false
    dialogues[dialogue_id] = data
    return true

func start(dialogue_id: String, state: Dictionary = {}) -> bool:
    if not dialogues.has(dialogue_id):
        return false
    active_id = dialogue_id
    cursor = 0
    waiting_for_choice = false
    _advance(state)
    return true

func choose(option_id: String, state: Dictionary = {}) -> void:
    if not waiting_for_choice:
        return
    var line: Dictionary = dialogues[active_id]["lines"][cursor]
    var next_index := -1
    for option in line.get("options", []):
        if str(option.get("id", "")) == option_id:
            next_index = int(option.get("next", cursor + 1))
            break
    if next_index < 0:
        return
    cursor = next_index
    waiting_for_choice = false
    _advance(state)

func continue_dialogue(state: Dictionary = {}) -> void:
    if active_id.is_empty() or waiting_for_choice:
        return
    cursor += 1
    _advance(state)

func _advance(state: Dictionary) -> void:
    var lines: Array = dialogues[active_id]["lines"]
    while cursor < lines.size():
        var line: Dictionary = lines[cursor]
        var required_flag := str(line.get("requires_flag", ""))
        if not required_flag.is_empty() and not bool(state.get(required_flag, false)):
            cursor += 1
            continue
        line_started.emit(line)
        if line.has("options"):
            waiting_for_choice = true
            choice_requested.emit(line["options"])
        return
    var finished_id := active_id
    active_id = ""
    dialogue_finished.emit(finished_id)
