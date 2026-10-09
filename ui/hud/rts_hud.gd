class_name RtsHud
extends Control
## HUD RTS : barre des ressources (haut), mini-carte (bas gauche), panneau de
## sélection (bas, à côté de la mini-carte), commandes et file de production (bas
## droite), ligne de messages. Lecture seule de la simulation ; les commandes passent
## par BuildingSystem / OrderSystem. Les panneaux arrêtent les clics (pas de
## sélection à travers le HUD) ; le reste de l'écran laisse passer la souris.

@export var economy: Economy
@export var player: PlayerState
@export var selection: SelectionController
@export var buildings: BuildingSystem
@export var simulation: UnitSimulation
@export var order_system: OrderSystem
@export var camera_rig: RTSCamera
## Habillage (vide : habillage par défaut).
@export var skin: HudSkin

@export_group("Disposition")
@export var margin: float = 8.0
@export var minimap_size: float = 176.0
@export var selection_width: float = 390.0
@export var message_duration: float = 3.0

var top_bar: HudTopBar
var minimap: HudMinimap
var selection_panel: HudSelectionPanel
var command_panel: HudCommandPanel

var _message: Label
var _message_time: float = 0.0


func _ready() -> void:
	if skin == null:
		skin = HudSkin.new()
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE

	top_bar = HudTopBar.new()
	add_child(top_bar)
	top_bar.setup(economy, player, skin)
	top_bar.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP, Control.PRESET_MODE_MINSIZE, margin)
	top_bar.grow_horizontal = Control.GROW_DIRECTION_BOTH

	var map_frame := PanelContainer.new()
	map_frame.add_theme_stylebox_override("panel", skin.make_panel_style())
	map_frame.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(map_frame)
	minimap = HudMinimap.new()
	minimap.custom_minimum_size = Vector2(minimap_size, minimap_size)
	map_frame.add_child(minimap)
	minimap.setup(camera_rig, simulation, buildings, selection, player, skin)
	map_frame.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT, Control.PRESET_MODE_MINSIZE, margin)
	map_frame.grow_vertical = Control.GROW_DIRECTION_BEGIN

	selection_panel = HudSelectionPanel.new()
	selection_panel.custom_minimum_size = Vector2(selection_width, 0.0)
	add_child(selection_panel)
	selection_panel.setup(selection, buildings, skin)
	selection_panel.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT, Control.PRESET_MODE_MINSIZE, margin)
	selection_panel.grow_vertical = Control.GROW_DIRECTION_BEGIN
	var shift := minimap_size + margin * 2.0 + 16.0
	selection_panel.offset_left += shift
	selection_panel.offset_right += shift

	command_panel = HudCommandPanel.new()
	add_child(command_panel)
	command_panel.setup(selection, buildings, order_system, player, skin)
	command_panel.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT, Control.PRESET_MODE_MINSIZE, margin)
	command_panel.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	command_panel.grow_vertical = Control.GROW_DIRECTION_BEGIN
	command_panel.message.connect(show_message)

	_message = Label.new()
	_message.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_message.add_theme_font_size_override("font_size", 18)
	_message.add_theme_color_override("font_outline_color", Color.BLACK)
	_message.add_theme_constant_override("outline_size", 6)
	_message.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_message)
	_message.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM, Control.PRESET_MODE_MINSIZE, 0.0)
	_message.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_message.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_message.offset_bottom = -(minimap_size + margin * 2.0 + 40.0)
	_message.visible = false


func _process(delta: float) -> void:
	# Panneaux ancrés : taille ramenée au contenu (qui change avec la sélection), coin
	# conservé.
	var area := size
	_dock(top_bar, Vector2((area.x - _content_size(top_bar).x) * 0.5, margin))
	_dock(minimap.get_parent() as Control, Vector2(margin, area.y - _content_size(minimap.get_parent() as Control).y - margin))
	var selection_size := _content_size(selection_panel)
	_dock(selection_panel, Vector2(minimap_size + margin * 2.0 + 16.0 + margin, area.y - selection_size.y - margin))
	var command_size := _content_size(command_panel)
	_dock(command_panel, Vector2(area.x - command_size.x - margin, area.y - command_size.y - margin))
	if _message_time > 0.0:
		_message_time -= delta
		_message.modulate.a = clampf(_message_time / 0.5, 0.0, 1.0)
		_message.visible = _message_time > 0.0


func _content_size(control: Control) -> Vector2:
	return control.get_combined_minimum_size()


func _dock(control: Control, position_on_screen: Vector2) -> void:
	control.set_anchors_preset(Control.PRESET_TOP_LEFT)
	control.size = _content_size(control)
	control.position = position_on_screen


## Message bref (refus d'une commande, production lancée…).
func show_message(text: String, is_error: bool = false) -> void:
	if text.is_empty():
		return
	_message.text = text
	_message.add_theme_color_override("font_color", skin.warning_color if is_error else skin.text_color)
	_message.visible = true
	_message_time = message_duration


func get_message() -> String:
	return _message.text if _message.visible else ""
