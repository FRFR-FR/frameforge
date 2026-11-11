extends Node
class_name GameForgeProfile

## Adaptive runtime policy. Hardware detection is deliberately conservative:
## Android starts on Low; desktop starts Balanced. Device benchmark profiles
## and player settings can raise/lower this after real hardware validation.

enum Tier { LOW, BALANCED, HIGH }

@export var android_default_tier: Tier = Tier.LOW
@export var desktop_default_tier: Tier = Tier.BALANCED
@export var allow_high_tier_on_mobile := false

var tier: Tier = Tier.BALANCED
var target_fps: int = 30

func _ready() -> void:
    tier = android_default_tier if OS.has_feature("mobile") else desktop_default_tier
    if OS.has_feature("mobile") and not allow_high_tier_on_mobile:
        tier = mini(tier, Tier.BALANCED) as Tier
    target_fps = 30 if tier == Tier.LOW else 60
    Engine.max_fps = target_fps
    _apply_profile()

func _apply_profile() -> void:
    var viewport := get_viewport()
    match tier:
        Tier.LOW:
            viewport.scaling_3d_scale = 0.75
        Tier.BALANCED:
            viewport.scaling_3d_scale = 0.9
        Tier.HIGH:
            viewport.scaling_3d_scale = 1.0

func set_quality_tier(new_tier: Tier) -> void:
    if OS.has_feature("mobile") and not allow_high_tier_on_mobile:
        new_tier = mini(new_tier, Tier.BALANCED) as Tier
    tier = new_tier
    target_fps = 30 if tier == Tier.LOW else 60
    Engine.max_fps = target_fps
    _apply_profile()
