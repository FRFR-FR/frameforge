extends Node
class_name GameForgeProfile

## Applies a conservative quality profile at startup.
## Profile selection is based on available runtime hints and can be overridden
## by the generated game's settings menu. Always profile on physical devices.

enum Tier { LOW, BALANCED, HIGH }

var tier: Tier = Tier.BALANCED
var target_fps: int = 30

func _ready() -> void:
    _select_profile()
    Engine.max_fps = target_fps
    _apply_profile()

func _select_profile() -> void:
    var processor := OS.get_processor_name().to_lower()
    var low_memory := OS.get_memory_info().get("physical", 0) < 3_000_000_000
    var mobile := OS.has_feature("mobile")
    if mobile and (low_memory or processor.contains("cortex-a") or processor.contains("mediatek") and low_memory):
        tier = Tier.LOW
        target_fps = 30
    elif mobile:
        tier = Tier.BALANCED
        target_fps = 30
    else:
        tier = Tier.HIGH
        target_fps = 60

func _apply_profile() -> void:
    match tier:
        Tier.LOW:
            ProjectSettings.set_setting("rendering/anti_aliasing/quality/msaa_3d", 0)
            ProjectSettings.set_setting("rendering/scaling_3d/scale", 0.75)
        Tier.BALANCED:
            ProjectSettings.set_setting("rendering/anti_aliasing/quality/msaa_3d", 2)
            ProjectSettings.set_setting("rendering/scaling_3d/scale", 0.9)
        Tier.HIGH:
            ProjectSettings.set_setting("rendering/anti_aliasing/quality/msaa_3d", 4)
            ProjectSettings.set_setting("rendering/scaling_3d/scale", 1.0)
