extends Node
class_name GameForgeFrameForgePlayer
## Runtime cue dispatcher. A host scene supplies shot camera transforms and cue handlers.
signal cue_fired(cue: Dictionary)
signal cinematic_finished(cinematic_id: String)
var timeline: Dictionary = {}
var elapsed := 0.0
var cursor := 0
var playing := false

func play(data: Dictionary) -> void:
    timeline = data
    elapsed = 0.0
    cursor = 0
    playing = true

func stop() -> void:
    playing = false

func _process(delta: float) -> void:
    if not playing:
        return
    elapsed += delta
    var events: Array = timeline.get("events", [])
    while cursor < events.size() and float(events[cursor]["at"]) <= elapsed:
        cue_fired.emit(events[cursor])
        cursor += 1
    if elapsed >= float(timeline.get("duration_seconds", 0.0)):
        playing = false
        cinematic_finished.emit(str(timeline.get("cinematic_id", "")))
