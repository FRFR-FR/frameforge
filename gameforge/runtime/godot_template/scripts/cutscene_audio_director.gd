extends Node
class_name GameForgeCutsceneAudioDirector

## One audio clock drives dialogue, subtitles and viseme events to avoid timer drift.
signal viseme_cue(character_id: String, cue: Dictionary)
signal cutscene_finished

@export var subtitle_layer_path: NodePath = NodePath("SubtitleLayer")

var _player: AudioStreamPlayer
var _subtitle_layer: GameForgeCutsceneSubtitleLayer
var _lines: Array = []
var _visemes: Array = []
var _line_index := 0
var _viseme_index := 0
var _active_visemes: Array[Dictionary] = []
var _active_line_id := ""
var _active_viseme_id := ""
var _timeline_duration := 0.0
var _playing := false

func _ready() -> void:
    _player = AudioStreamPlayer.new()
    _player.name = "DialogueAudio"
    add_child(_player)
    _subtitle_layer = GameForgeCutsceneSubtitleLayer.new()
    _subtitle_layer.name = "SubtitleLayer"
    add_child(_subtitle_layer)

func play_cutscene(audio_stream: AudioStream, alignment_manifest: Dictionary) -> void:
    stop_cutscene()
    _lines = alignment_manifest.get("lines", [])
    _visemes = alignment_manifest.get("visemes", [])
    _lines.sort_custom(func(a, b): return float(a.get("start", 0.0)) < float(b.get("start", 0.0)))
    _visemes.sort_custom(func(a, b): return float(a.get("at", 0.0)) < float(b.get("at", 0.0)))
    _line_index = 0
    _viseme_index = 0
    _active_line_id = ""
    _active_viseme_id = ""
    _active_visemes.clear()
    _timeline_duration = 0.0
    for line in _lines:
        _timeline_duration = maxf(_timeline_duration, float(line.get("end", 0.0)))
    _player.stream = audio_stream
    _player.play()
    _playing = true

func stop_cutscene() -> void:
    _playing = false
    if _player:
        _player.stop()
    if _subtitle_layer:
        _subtitle_layer.clear_subtitle()

func _process(_delta: float) -> void:
    if not _playing:
        return
    var clock := _player.get_playback_position()
    while _line_index < _lines.size() and float(_lines[_line_index].get("start", 0.0)) <= clock:
        var line: Dictionary = _lines[_line_index]
        _active_line_id = str(line.get("id", ""))
        _subtitle_layer.show_subtitle(str(line.get("text", "")))
        _line_index += 1
    if not _active_line_id.is_empty():
        var active := _find_active_line(clock)
        if active.is_empty():
            _active_line_id = ""
            _subtitle_layer.clear_subtitle()

    while _viseme_index < _visemes.size() and float(_visemes[_viseme_index].get("at", 0.0)) <= clock:
        var cue: Dictionary = _visemes[_viseme_index]
        _active_viseme_id = str(cue.get("character_id", "")) + ":" + str(cue.get("dialogue_id", "")) + ":" + str(_viseme_index)
        viseme_cue.emit(str(cue.get("character_id", "")), cue)
        _active_visemes.append(cue)
        _viseme_index += 1

    # Return the jaw to neutral at the measured end time of each aligned character cue.
    for index in range(_active_visemes.size() - 1, -1, -1):
        var active_cue: Dictionary = _active_visemes[index]
        if clock >= float(active_cue.get("end", clock)):
            var neutral_cue := active_cue.duplicate(true)
            neutral_cue["jaw_open"] = 0.0
            neutral_cue["viseme"] = "neutral"
            neutral_cue["ended"] = true
            viseme_cue.emit(str(neutral_cue.get("character_id", "")), neutral_cue)
            _active_visemes.remove_at(index)

    if clock >= _timeline_duration and not _player.playing:
        stop_cutscene()
        cutscene_finished.emit()

func _find_active_line(clock: float) -> Dictionary:
    for line in _lines:
        if float(line.get("start", 0.0)) <= clock and clock <= float(line.get("end", 0.0)):
            return line
    return {}
