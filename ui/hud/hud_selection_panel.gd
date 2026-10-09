class_name HudSelectionPanel
extends PanelContainer
## Panneau de l'objet sélectionné : portrait, nom, faction, points de vie, état et
## production. Même présentation pour un bâtiment, une escouade ou plusieurs
## escouades. Construit une fois ; seules les valeurs changent (lues à chaque image).

var selection: SelectionController
var buildings: BuildingSystem
var skin: HudSkin

var _portrait: HudPortrait
var _title: Label
var _subtitle: Label
var _hp_bar: ProgressBar
var _hp_fill: StyleBoxFlat
var _hp_text: Label
var _state: Label
var _detail: Label


func setup(p_selection: SelectionController, p_buildings: BuildingSystem, p_skin: HudSkin) -> void:
	selection = p_selection
	buildings = p_buildings
	skin = p_skin
	mouse_filter = Control.MOUSE_FILTER_STOP
	add_theme_stylebox_override("panel", skin.make_panel_style())
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	add_child(row)
	_portrait = HudPortrait.new()
	_portrait.custom_minimum_size = Vector2(96, 96)
	_portrait.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	row.add_child(_portrait)
	var column := VBoxContainer.new()
	column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	column.add_theme_constant_override("separation", 2)
	row.add_child(column)
	_title = _label(19, skin.text_color)
	_subtitle = _label(13, skin.muted_text_color)
	column.add_child(_title)
	column.add_child(_subtitle)
	var hp_row := HBoxContainer.new()
	_hp_bar = ProgressBar.new()
	_hp_bar.show_percentage = false
	_hp_bar.custom_minimum_size = Vector2(150, 14)
	_hp_bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	_hp_bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_hp_fill = StyleBoxFlat.new()
	_hp_fill.set_corner_radius_all(3)
	_hp_bar.add_theme_stylebox_override("fill", _hp_fill)
	_hp_text = _label(13, skin.text_color)
	_hp_text.clip_text = false
	hp_row.add_child(_hp_bar)
	hp_row.add_child(_hp_text)
	column.add_child(hp_row)
	_state = _label(14, skin.text_color)
	_detail = _label(13, skin.muted_text_color)
	column.add_child(_state)
	column.add_child(_detail)


func _process(_delta: float) -> void:
	var building := selection.selected_building
	var squads := selection.selected_squads
	visible = building != null or not squads.is_empty()
	if building != null:
		_show_building(building)
	elif squads.size() == 1:
		_show_squad(squads[0])
	elif squads.size() > 1:
		_show_squads(squads)


func _show_building(building: Building) -> void:
	var data := building.data
	var faction := data.faction
	var color := faction.unit_color if faction != null else Color.WHITE
	_portrait.show_subject(data.get_portrait(), data.display_name, color)
	_title.text = data.display_name
	_subtitle.text = "%s · %s" % [faction.display_name if faction != null else "", "Quartier général" if data.is_headquarters else "Bâtiment"]
	_subtitle.add_theme_color_override("font_color", color.lightened(0.2))
	_set_hp(building.hp, data.max_hp)
	match building.state:
		Building.State.ACTIVE:
			_state.text = "Opérationnel"
		Building.State.CONSTRUCTING:
			_state.text = "En construction : %d %%" % roundi(building.construction_progress * 100.0)
		Building.State.DESTROYED:
			_state.text = "Détruit"
	var queue := building.queue
	if queue.is_empty():
		_detail.text = "Aucune production en cours"
	else:
		var current := queue.current()
		var waiting := queue.state == ProductionQueue.State.WAITING_FOR_EXIT
		_detail.text = "Production : %s — %s%s" % [HudCommandPanel.unit_name(current),
			"en attente d'une sortie libre" if waiting else "%d s" % ceili(queue.remaining_time()),
			" (+%d en file)" % (queue.items.size() - 1) if queue.items.size() > 1 else ""]
	tooltip_text = data.description


func _show_squad(squad: Squad) -> void:
	var data := squad.data
	var unit_data := data.unit_data
	var faction := unit_data.faction
	var color := faction.unit_color if faction != null else Color.WHITE
	_portrait.show_subject(data.get_portrait(), HudCommandPanel.unit_name(data), color)
	_title.text = HudCommandPanel.unit_name(data)
	_subtitle.text = "%s · escouade n° %d" % [faction.display_name if faction != null else "", squad.id + 1]
	_subtitle.add_theme_color_override("font_color", color.lightened(0.2))
	var hp := 0.0
	for unit in squad.units:
		hp += unit.health
	_set_hp(hp, unit_data.member_hp * data.unit_count)
	_state.text = "%s · %d / %d membres" % [_squad_state(squad), squad.units.size(), data.unit_count]
	_detail.text = "Dégâts %s · portée %s m · cadence %s s" % [str(unit_data.damage_per_shot),
		str(unit_data.attack_range), str(unit_data.attack_cooldown)]
	tooltip_text = UnitInfoPanel.describe(squad)


func _show_squads(squads: Array[Squad]) -> void:
	var first := squads[0].data.unit_data.faction
	var color := first.unit_color if first != null else Color.WHITE
	_portrait.show_subject(null, "%d" % squads.size(), color)
	_title.text = "%d escouades" % squads.size()
	_subtitle.text = first.display_name if first != null else ""
	var hp := 0.0
	var max_hp := 0.0
	var names: PackedStringArray = []
	for squad in squads:
		for unit in squad.units:
			hp += unit.health
		max_hp += squad.data.unit_data.member_hp * squad.data.unit_count
		if names.size() < 6:
			names.append(HudCommandPanel.unit_name(squad.data))
	_set_hp(hp, max_hp)
	_state.text = "Sélection de groupe"
	_detail.text = ", ".join(names) + ("…" if squads.size() > 6 else "")
	tooltip_text = ""


func _set_hp(hp: float, max_hp: float) -> void:
	_hp_bar.max_value = maxf(max_hp, 1.0)
	_hp_bar.value = hp
	_hp_text.text = " %d / %d" % [roundi(hp), roundi(max_hp)]
	_hp_fill.bg_color = Color(0.85, 0.25, 0.2).lerp(Color(0.35, 0.85, 0.35), hp / maxf(max_hp, 1.0))


static func _squad_state(squad: Squad) -> String:
	if squad.order is AttackOrder:
		return "Attaque"
	if squad.order is MoveOrder:
		return "En déplacement"
	return "En position"


func _label(font_size: int, color: Color) -> Label:
	var label := Label.new()
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	label.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
	label.add_theme_constant_override("outline_size", 3)
	label.clip_text = true
	return label
