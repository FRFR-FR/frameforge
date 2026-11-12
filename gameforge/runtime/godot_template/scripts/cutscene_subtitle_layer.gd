extends CanvasLayer
class_name GameForgeCutsceneSubtitleLayer

## Subtitle label has no panel/stylebox: background remains fully transparent.
@export var bottom_margin := 38
@export var font_size := 30
@export var outline_size := 4

var _label: Label
var _hide_at := -1.0

func _ready() -> void:
    _label = Label.new()
    _label.name = "SubtitleText"
    _label.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
    _label.offset_left = 28
    _label.offset_right = -28
    _label.offset_top = -120
    _label.offset_bottom = -bottom_margin
    _label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    _label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
    _label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    _label.add_theme_font_size_override("font_size", font_size)
    _label.add_theme_color_override("font_color", Color(1, 1, 1, 1))
    _label.add_theme_color_override("font_outline_color", Color(0.015, 0.02, 0.03, 0.98))
    _label.add_theme_constant_override("outline_size", outline_size)
    # Deliberately do not add a Panel, ColorRect, or opaque StyleBox.
    add_child(_label)
    _label.text = ""
    _label.visible = false

func show_subtitle(text: String, duration: float = 0.0) -> void:
    if not _label:
        return
    _label.text = text
    _label.visible = not text.strip_edges().is_empty()
    _hide_at = duration

func clear_subtitle() -> void:
    if _label:
        _label.text = ""
        _label.visible = false
    _hide_at = -1.0

func set_subtitle_scale(scale: float) -> void:
    if _label:
        _label.add_theme_font_size_override("font_size", int(round(font_size * clampf(scale, 0.75, 1.8))))
