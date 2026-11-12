extends Node
class_name GameForgeCutsceneCharacterLipSync

## Attach to a character root. Assign the imported Skeleton3D path; the rig must
## contain a bone named "jaw" (or set jaw_bone_name). Add the character root to
## group "gameforge_character_<character_id>" to receive timeline cues.
@export var skeleton_path: NodePath
@export var jaw_bone_name := "jaw"
@export_range(1.0, 35.0, 0.5) var maximum_jaw_degrees := 18.0

var _skeleton: Skeleton3D
var _jaw_bone := -1
var _rest_rotation := Quaternion.IDENTITY

func _ready() -> void:
    _skeleton = get_node_or_null(skeleton_path) as Skeleton3D
    if not _skeleton:
        push_warning("GAMEFORGE lip-sync: Skeleton3D was not found at skeleton_path.")
        return
    _jaw_bone = _skeleton.find_bone(jaw_bone_name)
    if _jaw_bone < 0:
        push_warning("GAMEFORGE lip-sync: jaw bone not found: " + jaw_bone_name)
        return
    _rest_rotation = _skeleton.get_bone_pose_rotation(_jaw_bone)

func apply_lip_sync_cue(cue: Dictionary) -> void:
    if not _skeleton or _jaw_bone < 0:
        return
    var openness := clampf(float(cue.get("jaw_open", 0.0)), 0.0, 1.0)
    var angle := deg_to_rad(-maximum_jaw_degrees * openness)
    var jaw_delta := Quaternion(Vector3.RIGHT, angle)
    _skeleton.set_bone_pose_rotation(_jaw_bone, _rest_rotation * jaw_delta)
