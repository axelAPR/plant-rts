class_name SelectionBox
extends Control
## Cadre de sélection affiché pendant un glisser de la souris.

@export var fill_color: Color = Color(0.45, 1.0, 0.45, 0.12)
@export var border_color: Color = Color(0.55, 1.0, 0.55, 0.9)
@export var border_width: float = 1.5

var _rect: Rect2


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_preset(Control.PRESET_FULL_RECT)
	visible = false


func show_box(rect: Rect2) -> void:
	_rect = rect
	visible = true
	queue_redraw()


func hide_box() -> void:
	visible = false


func _draw() -> void:
	draw_rect(_rect, fill_color)
	draw_rect(_rect, border_color, false, border_width)
