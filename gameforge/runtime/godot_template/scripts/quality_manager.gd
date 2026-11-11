extends Node
class_name GameForgeQualityManager
## Runtime adaptive quality policy; never promises a fixed FPS without device profiling.
@export var target_fps := 30.0
@export var sample_window := 2.0
@export var minimum_scale := 0.65
@export var maximum_scale := 1.0
var samples: Array[float] = []
var elapsed := 0.0
var scale := 1.0
var tier := "balanced"

func _process(delta: float) -> void:
    samples.append(delta)
    elapsed += delta
    if elapsed < sample_window:
        return
    var total := 0.0
    for sample in samples:
        total += sample
    var average := total / maxf(1.0, float(samples.size()))
    var fps := 1.0 / maxf(0.0001, average)
    if fps < target_fps * 0.88:
        scale = maxf(minimum_scale, scale - 0.05)
    elif fps > target_fps * 1.08:
        scale = minf(maximum_scale, scale + 0.025)
    _apply_scale()
    samples.clear()
    elapsed = 0.0

func _apply_scale() -> void:
    var viewport := get_viewport()
    if viewport:
        viewport.scaling_3d_scale = scale
    tier = "performance" if scale < 0.78 else ("balanced" if scale < 0.95 else "quality")
