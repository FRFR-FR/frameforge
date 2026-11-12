extends Node
class_name GameForgeSaveManager
signal save_completed(slot: String)
signal save_failed(slot: String, reason: String)
const SAVE_DIRECTORY := "user://saves"
const SAVE_VERSION := 1

func save_game(slot: String, payload: Dictionary) -> bool:
    if slot.is_empty() or slot.contains("/") or slot.contains("\\"):
        save_failed.emit(slot, "Invalid save slot.")
        return false
    var directory := DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(SAVE_DIRECTORY))
    if directory != OK and directory != ERR_ALREADY_EXISTS:
        save_failed.emit(slot, "Could not create save directory.")
        return false
    var data := {"version": SAVE_VERSION, "saved_at_unix": int(Time.get_unix_time_from_system()), "payload": payload}
    var path := SAVE_DIRECTORY.path_join(slot + ".json")
    var file := FileAccess.open(path, FileAccess.WRITE)
    if file == null:
        save_failed.emit(slot, "Could not open save file.")
        return false
    file.store_string(JSON.stringify(data))
    file.close()
    save_completed.emit(slot)
    return true

func load_game(slot: String) -> Dictionary:
    if slot.is_empty() or slot.contains("/") or slot.contains("\\"):
        return {}
    var path := SAVE_DIRECTORY.path_join(slot + ".json")
    if not FileAccess.file_exists(path):
        return {}
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        return {}
    var parsed = JSON.parse_string(file.get_as_text())
    file.close()
    if not parsed is Dictionary or int(parsed.get("version", -1)) != SAVE_VERSION:
        return {}
    var payload = parsed.get("payload", {})
    return payload if payload is Dictionary else {}
