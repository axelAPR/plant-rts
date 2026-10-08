class_name ResourceBar
extends Control
## Barre de ressources, en haut au centre de l'écran : pour chaque ressource du camp,
## une pastille et le nom à sa couleur, le stock possédé et le revenu par minute.
## Lit l'économie sans jamais la modifier.

@export var economy: Economy
## Camps affichés, un rang chacun (le camp du joueur ; plusieurs en développement).
@export var teams: Array[int] = [0]
## Marge (pixels) entre la barre et le haut de l'écran.
@export var screen_margin: float = 8.0

@export_group("Apparence")
@export var amount_font_size: int = 20
@export var detail_font_size: int = 14
@export var icon_size: float = 14.0
@export var background_color: Color = Color(0.08, 0.1, 0.08, 0.78)

## Libellés d'une ressource d'un camp, et dernières valeurs affichées.
class ResourceView:
	var team_economy: TeamEconomy
	var kind: TeamEconomy.Kind
	var amount_label: Label
	var income_label: Label
	var shown_amount: int = -1
	var shown_income: float = NAN


var _views: Array[ResourceView] = []
var _rows: VBoxContainer


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var panel := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = background_color
	style.set_corner_radius_all(8)
	style.set_content_margin_all(8)
	style.content_margin_left = 14
	style.content_margin_right = 14
	panel.add_theme_stylebox_override("panel", style)
	panel.mouse_filter = Control.MOUSE_FILTER_STOP
	panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP, Control.PRESET_MODE_MINSIZE, int(screen_margin))
	panel.grow_horizontal = Control.GROW_DIRECTION_BOTH
	add_child(panel)
	_rows = VBoxContainer.new()
	_rows.add_theme_constant_override("separation", 6)
	panel.add_child(_rows)
	# L'économie crée ses camps dans son _ready, qui peut passer après celui-ci.
	economy.team_added.connect(func(_team_economy: TeamEconomy) -> void: _rebuild())
	_rebuild()


func _process(_delta: float) -> void:
	for view in _views:
		var amount := view.team_economy.get_amount(view.kind)
		if amount != view.shown_amount:
			view.shown_amount = amount
			view.amount_label.text = str(amount)
		var income := view.team_economy.get_income_per_minute(view.kind)
		if income != view.shown_income:
			view.shown_income = income
			view.income_label.text = "%s%s/min" % ["+" if income >= 0.0 else "", _format_number(income)]


func _rebuild() -> void:
	for child in _rows.get_children():
		child.queue_free()
	_views.clear()
	for team in teams:
		var team_economy := economy.get_team(team)
		if team_economy != null:
			_rows.add_child(_make_row(team_economy))


func _make_row(team_economy: TeamEconomy) -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 22)
	if teams.size() > 1:
		row.add_child(_make_label(team_economy.faction.display_name, detail_font_size, Color(1, 1, 1, 0.7)))
	for index in TeamEconomy.KIND_COUNT:
		var kind := index as TeamEconomy.Kind
		var color := team_economy.faction.get_resource_color(kind)
		var group := HBoxContainer.new()
		group.add_theme_constant_override("separation", 6)
		group.add_child(_make_icon(color))
		group.add_child(_make_label(team_economy.faction.get_resource_name(kind), detail_font_size, color))
		var view := ResourceView.new()
		view.team_economy = team_economy
		view.kind = kind
		view.amount_label = _make_label("0", amount_font_size, Color.WHITE)
		view.amount_label.custom_minimum_size.x = amount_font_size * 2.6
		view.amount_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		view.income_label = _make_label("", detail_font_size, color.lightened(0.15))
		group.add_child(view.amount_label)
		group.add_child(view.income_label)
		row.add_child(group)
		_views.append(view)
	return row


## Pastille ronde à la couleur de la ressource.
func _make_icon(color: Color) -> Panel:
	var icon := Panel.new()
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.set_corner_radius_all(int(icon_size))
	style.border_color = color.darkened(0.45)
	style.set_border_width_all(2)
	icon.add_theme_stylebox_override("panel", style)
	icon.custom_minimum_size = Vector2.ONE * icon_size
	icon.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	return icon


func _make_label(text: String, font_size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	label.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.85))
	label.add_theme_constant_override("outline_size", 4)
	label.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	return label


## Nombre sans décimale s'il est entier (200), sinon une décimale (2.5).
func _format_number(value: float) -> String:
	return str(int(value)) if is_equal_approx(value, roundf(value)) else "%.1f" % value
