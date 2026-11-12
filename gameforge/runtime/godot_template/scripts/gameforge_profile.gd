extends Node
class_name GameForgeProfile

## Runtime low-end governor for generated games. Android starts conservatively;
## measured frame time can lower 3D scale without changing the UI resolution.

signal profile_changed(profile: Dictionary)

enum Tier { LOW, BALANCED, HIGH }

@export var sample_interval := 2.0
@export var low_fps_threshold := 27.0
@export var recovery_fps_threshold := 34.0
@export var allow_high_tier_on_mobile := false

var tier: Tier = Tier.BALANCED
var target_fps := 60
var render_scale := 0.90
var _sample_elapsed := 0.0
var _frame_samples: Array[float] = []
var _memory_budget_mb := 1200.0

func _ready() -> void:
    tier = _detect_starting_tier()
    _apply_profile()
    profile_changed.emit(get_profile_report())

func _detect_starting_tier() -> Tier:
    var mobile := OS.has_feature("mobile") or OS.get_name() in ["Android", "iOS"]
    var cores := OS.get_processor_count()
    if mobile:
        if cores <= 4:
            return Tier.LOW
        return Tier.BALANCED
    return Tier.BALANCED

func _process(delta: float) -> void:
    _sample_elapsed += delta
    _frame_samples.append(delta)
    if _sample_elapsed < sample_interval:
        return
    var total := 0.0
    for sample in _frame_samples:
        total += sample
    var average := total / maxf(1.0, float(_frame_samples.size()))
    var fps := 1.0 / maxf(0.0001, average)
    var memory_mb := float(OS.get_static_memory_usage()) / 1048576.0

    var changed := false
    if fps < low_fps_threshold or memory_mb > _memory_budget_mb:
        changed = _step_down()
    elif fps > recovery_fps_threshold and memory_mb < _memory_budget_mb * 0.72:
        changed = _step_up()
    _frame_samples.clear()
    _sample_elapsed = 0.0
    if changed:
        _apply_profile()
        profile_changed.emit(get_profile_report())

func _step_down() -> bool:
    var previous := tier
    if tier == Tier.HIGH:
        tier = Tier.BALANCED
    elif tier == Tier.BALANCED:
        tier = Tier.LOW
    return previous != tier

func _step_up() -> bool:
    if OS.has_feature("mobile") and not allow_high_tier_on_mobile:
        return false
    var previous := tier
    if tier == Tier.LOW:
        tier = Tier.BALANCED
    elif tier == Tier.BALANCED and not OS.has_feature("mobile"):
        tier = Tier.HIGH
    return previous != tier

func set_quality_tier(new_tier: Tier) -> void:
    if OS.has_feature("mobile") and not allow_high_tier_on_mobile and new_tier == Tier.HIGH:
        new_tier = Tier.BALANCED
    tier = new_tier
    _apply_profile()
    profile_changed.emit(get_profile_report())

func _apply_profile() -> void:
    var viewport := get_viewport()
    match tier:
        Tier.LOW:
            target_fps = 30
            render_scale = 0.65
            _memory_budget_mb = 650.0
            viewport.msaa_3d = Viewport.MSAA_DISABLED
            viewport.screen_space_aa = Viewport.SCREEN_SPACE_AA_DISABLED
        Tier.BALANCED:
            target_fps = 45
            render_scale = 0.82
            _memory_budget_mb = 1050.0
            viewport.msaa_3d = Viewport.MSAA_DISABLED
            viewport.screen_space_aa = Viewport.SCREEN_SPACE_AA_DISABLED
        Tier.HIGH:
            target_fps = 60
            render_scale = 1.0
            _memory_budget_mb = 1800.0
            viewport.msaa_3d = Viewport.MSAA_2X
            viewport.screen_space_aa = Viewport.SCREEN_SPACE_AA_FXAA
    viewport.scaling_3d_scale = render_scale
    Engine.max_fps = target_fps

func get_profile_report() -> Dictionary:
    var names := {Tier.LOW: "low", Tier.BALANCED: "balanced", Tier.HIGH: "high"}
    return {
        "tier": names[tier],
        "target_fps": target_fps,
        "render_scale": render_scale,
        "memory_budget_mb": _memory_budget_mb,
        "cpu_threads": OS.get_processor_count(),
        "device": OS.get_name()
    }
