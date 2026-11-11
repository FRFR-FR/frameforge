extends Node
class_name GameForgeNarrativeState

## Typed-by-convention narrative state store. Generated games should define
## their state schema and validate keys/types before scenes are packaged.

signal state_changed(key: String, value: Variant)

var values: Dictionary = {}

func set_value(key: String, value: Variant) -> void:
    if key.strip_edges().is_empty():
        push_error("Narrative state key cannot be empty.")
        return
    values[key] = value
    state_changed.emit(key, value)

func get_value(key: String, fallback: Variant = null) -> Variant:
    return values.get(key, fallback)

func has_flag(key: String) -> bool:
    return bool(values.get(key, false))

func export_save_data() -> Dictionary:
    return values.duplicate(true)

func import_save_data(data: Dictionary) -> void:
    values = data.duplicate(true)
