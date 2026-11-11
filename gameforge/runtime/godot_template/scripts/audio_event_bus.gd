extends Node
class_name GameForgeAudioEventBus

## Central event entry point for generated gameplay audio. Game projects bind
## event IDs to AudioStream resources in data; no asset paths are hardcoded.

signal audio_event_requested(event_id: String, position: Vector3, options: Dictionary)

func emit_2d(event_id: String, options: Dictionary = {}) -> void:
    audio_event_requested.emit(event_id, Vector3.ZERO, options)

func emit_3d(event_id: String, world_position: Vector3, options: Dictionary = {}) -> void:
    audio_event_requested.emit(event_id, world_position, options)
