extends Node
class_name GameForgeVFXEventBus

## Data-driven VFX dispatch. Concrete effect scenes are registered by generated
## projects and spawned by a project-specific effect router.

signal vfx_event_requested(event_id: String, world_transform: Transform3D, payload: Dictionary)

func emit_effect(event_id: String, world_transform: Transform3D, payload: Dictionary = {}) -> void:
    if event_id.strip_edges().is_empty():
        push_warning("Ignoring VFX event with empty ID.")
        return
    vfx_event_requested.emit(event_id, world_transform, payload)
