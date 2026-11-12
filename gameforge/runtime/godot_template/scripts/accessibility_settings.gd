extends Node
class_name GameForgeAccessibilitySettings
signal settings_changed(settings: Dictionary)
var settings := {"subtitles":true,"subtitle_scale":1.0,"camera_shake":true,"reduced_flashing":false,"hold_to_toggle":false,"text_scale":1.0,"color_filter":"none"}

func update_setting(key: String, value: Variant) -> bool:
    if not settings.has(key):
        return false
    settings[key] = value
    settings_changed.emit(settings.duplicate(true))
    return true

func get_settings() -> Dictionary:
    return settings.duplicate(true)
