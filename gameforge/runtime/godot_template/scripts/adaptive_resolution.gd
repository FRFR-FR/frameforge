extends Node
class_name GameForgeAdaptiveResolution

## Gentle runtime resolution controller. It changes only 3D render scale and
## leaves UI resolution untouched. Use after loading the profile manager.
## Actual thresholds should be tuned using repeatable device benchmarks.

@export var profile: GameForgeProfile
@export var sample_interval := 2.0
@export var low_fps_threshold := 27.0
@export var recovery_fps_threshold := 34.0
@export var minimum_scale := 0.65
@export var maximum_scale := 1.0
@export var scale_step := 0.05

var _sample_elapsed := 0.0
var _current_scale := 1.0

func _ready() -> void:
    _current_scale = get_viewport().scaling_3d_scale

func _process(delta: float) -> void:
    _sample_elapsed += delta
    if _sample_elapsed < sample_interval:
        return
    _sample_elapsed = 0.0

    var fps := Engine.get_frames_per_second()
    if fps < low_fps_threshold:
        _set_scale(maxf(minimum_scale, _current_scale - scale_step))
    elif fps > recovery_fps_threshold:
        _set_scale(minf(maximum_scale, _current_scale + scale_step))

func _set_scale(value: float) -> void:
    _current_scale = snappedf(value, scale_step)
    get_viewport().scaling_3d_scale = _current_scale
