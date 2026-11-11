extends Node
class_name GameForgeDialogueTimeline

## Dialogue and cinematic cues share a single authored timeline.
## Audio/voice assets are optional; subtitles remain available as fallback.

signal cue_started(cue: Dictionary)
signal cue_finished(cue: Dictionary)
signal timeline_finished

@export var cues: Array[Dictionary] = []
var _elapsed := 0.0
var _index := 0
var _playing := false

func play_from_start() -> void:
    _elapsed = 0.0
    _index = 0
    _playing = true

func stop() -> void:
    _playing = false

func _process(delta: float) -> void:
    if not _playing:
        return
    _elapsed += delta
    while _index < cues.size() and float(cues[_index].get("start", 0.0)) <= _elapsed:
        var cue := cues[_index]
        cue_started.emit(cue)
        _index += 1
    if _index >= cues.size():
        _playing = false
        timeline_finished.emit()

func seek(seconds: float) -> void:
    _elapsed = maxf(0.0, seconds)
    _index = 0
    while _index < cues.size() and float(cues[_index].get("start", 0.0)) < _elapsed:
        _index += 1
