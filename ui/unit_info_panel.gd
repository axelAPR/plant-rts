class_name UnitInfoPanel
extends Control
## Panneau de débogage, en bas à gauche : statistiques de l'escouade sélectionnée
## (la première si plusieurs) — nom, faction, membres vivants, HP, dégâts, précision,
## cadence, portée, projectile, coût et population. Lit l'état sans le modifier.

@export var selection: SelectionController
## Marge (pixels) entre le panneau et les bords de l'écran.
@export var screen_margin: float = 12.0
@export var font_size: int = 15
@export var background_color: Color = Color(0.08, 0.1, 0.08, 0.82)

var _panel: PanelContainer
var _label: Label


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel = PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = background_color
	style.set_corner_radius_all(8)
	style.set_content_margin_all(10)
	_panel.add_theme_stylebox_override("panel", style)
	_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT, Control.PRESET_MODE_MINSIZE, int(screen_margin))
	_panel.grow_vertical = Control.GROW_DIRECTION_BEGIN
	add_child(_panel)
	_label = Label.new()
	_label.add_theme_font_size_override("font_size", font_size)
	_label.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.85))
	_label.add_theme_constant_override("outline_size", 3)
	_panel.add_child(_label)
	_panel.visible = false


func _process(_delta: float) -> void:
	var squads := selection.selected_squads
	_panel.visible = not squads.is_empty()
	if squads.is_empty():
		return
	var text := describe(squads[0])
	if squads.size() > 1:
		text += "\n(+%d autre%s escouade%s)" % [squads.size() - 1, "s" if squads.size() > 2 else "",
				"s" if squads.size() > 2 else ""]
	if _label.text != text:
		_label.text = text


## Description d'une escouade, une statistique par ligne.
static func describe(squad: Squad) -> String:
	var data := squad.data
	var unit := data.unit_data
	var faction := unit.faction
	var lines: Array[String] = []
	lines.append(unit.display_name)
	lines.append("Faction : %s" % (faction.display_name if faction != null else "—"))
	if data.is_individual():
		var health := squad.units[0].health if not squad.units.is_empty() else 0.0
		lines.append("Unité individuelle")
		lines.append("HP : %s / %s" % [_number(health), _number(unit.member_hp)])
	else:
		lines.append("%d / %d membres" % [squad.units.size(), data.unit_count])
		lines.append("HP : %s / membre" % _number(unit.member_hp))
		var healths: Array[String] = []
		for member in squad.units:
			healths.append(_number(member.health))
		lines.append("   (%s)" % " · ".join(healths))
	if unit.can_attack():
		lines.append("Dégâts : %s / tir" % _number(unit.damage_per_shot))
		lines.append("Précision : %d %%" % roundi(unit.accuracy * 100.0))
		lines.append("Cadence : %s s" % _number(unit.attack_cooldown))
		lines.append("Portée : %s m" % _number(unit.attack_range))
		if unit.is_melee():
			lines.append("Projectile : aucun (mêlée)")
		else:
			lines.append("Projectile : %s, %s m/s" % [unit.projectile.display_name, _number(unit.projectile_speed)])
	else:
		lines.append("N'attaque pas")
	lines.append("Coût : %s" % _cost_text(data, faction))
	lines.append("Population : %d" % data.population_cost)
	return "\n".join(lines)


static func _cost_text(data: SquadData, faction: FactionData) -> String:
	var cost := data.get_cost()
	var parts: Array[String] = []
	for kind in TeamEconomy.KIND_COUNT:
		var name := faction.get_resource_name(kind as TeamEconomy.Kind) if faction != null else "R%d" % (kind + 1)
		parts.append("%d %s" % [cost[kind], name])
	return " · ".join(parts)


## Nombre sans décimale s'il est entier, sinon une décimale.
static func _number(value: float) -> String:
	return str(int(value)) if is_equal_approx(value, roundf(value)) else "%.1f" % value
