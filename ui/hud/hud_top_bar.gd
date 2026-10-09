class_name HudTopBar
extends PanelContainer
## Barre supérieure du HUD : les trois ressources du camp du joueur (nom et couleur de
## sa faction, stock, revenu par minute) et la population utilisée / maximale.
## Valeurs lues dans TeamEconomy à chaque image (aucune copie indépendante).

var economy: Economy
var player: PlayerState
var skin: HudSkin

var _team_economy: TeamEconomy
var _icons: Array[Panel] = []
var _names: Array[Label] = []
var _amounts: Array[Label] = []
var _incomes: Array[Label] = []
var _population: Label


func setup(p_economy: Economy, p_player: PlayerState, p_skin: HudSkin) -> void:
	economy = p_economy
	player = p_player
	skin = p_skin
	mouse_filter = Control.MOUSE_FILTER_STOP
	add_theme_stylebox_override("panel", skin.make_panel_style())
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 18)
	add_child(row)
	for kind in TeamEconomy.KIND_COUNT:
		var item := HBoxContainer.new()
		item.add_theme_constant_override("separation", 6)
		var icon := Panel.new()
		icon.custom_minimum_size = Vector2(18, 18)
		icon.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		item.add_child(icon)
		var texts := VBoxContainer.new()
		texts.add_theme_constant_override("separation", -4)
		var name := _label(13, skin.muted_text_color)
		var amount_line := HBoxContainer.new()
		var amount := _label(20, skin.text_color)
		var income := _label(13, skin.muted_text_color)
		income.size_flags_vertical = Control.SIZE_SHRINK_END
		amount_line.add_child(amount)
		amount_line.add_child(income)
		texts.add_child(name)
		texts.add_child(amount_line)
		item.add_child(texts)
		row.add_child(item)
		_icons.append(icon)
		_names.append(name)
		_amounts.append(amount)
		_incomes.append(income)
	row.add_child(VSeparator.new())
	var pop_box := VBoxContainer.new()
	pop_box.add_theme_constant_override("separation", -4)
	pop_box.add_child(_label(13, skin.muted_text_color, "Population"))
	_population = _label(20, skin.text_color)
	pop_box.add_child(_population)
	row.add_child(pop_box)
	player.team_changed.connect(func(_team: int) -> void: _bind())
	_bind()


func _bind() -> void:
	_team_economy = economy.get_team(player.team)
	if _team_economy == null:
		return
	var faction := _team_economy.faction
	for kind in TeamEconomy.KIND_COUNT:
		var style := StyleBoxFlat.new()
		style.bg_color = faction.get_resource_color(kind)
		style.set_corner_radius_all(9)
		style.border_color = Color(0, 0, 0, 0.6)
		style.set_border_width_all(1)
		_icons[kind].add_theme_stylebox_override("panel", style)
		_names[kind].text = faction.get_resource_name(kind)
		_names[kind].add_theme_color_override("font_color", faction.get_resource_color(kind).lightened(0.2))


func _process(_delta: float) -> void:
	if _team_economy == null:
		return
	for kind in TeamEconomy.KIND_COUNT:
		_amounts[kind].text = str(_team_economy.get_amount(kind))
		var income := _team_economy.get_income_per_minute(kind)
		_incomes[kind].text = " %s%s/min" % ["+" if income >= 0.0 else "", _number(income)]
	_population.text = "%d / %d" % [_team_economy.population_used, _team_economy.population_cap]
	var full := _team_economy.get_population_free() <= 0
	_population.add_theme_color_override("font_color", skin.warning_color if full else skin.text_color)


func _label(font_size: int, color: Color, text: String = "") -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	label.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
	label.add_theme_constant_override("outline_size", 3)
	return label


static func _number(value: float) -> String:
	return str(roundi(value)) if is_equal_approx(value, roundf(value)) else "%.1f" % value
