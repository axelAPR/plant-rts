class_name DevMenu
extends Control
## Menu de développement, en haut à droite de l'écran :
## - « Toutes les troupes » : une escouade de chaque troupe autour du point visé par la
##   caméra, plantes (camp 0) au sud, zombies (camp 1) au nord, face à face ;
## - un bouton par troupe, rangés par camp : une escouade de cette troupe, de son côté
##   du point visé (plusieurs clics → plusieurs escouades côte à côte) ;
## - « Tout supprimer » : retire toutes les escouades.
## Chaque escouade prend l'emplacement libre le plus proche : pas d'apparition
## par-dessus des escouades existantes. Apparitions gratuites (hors production).
## F1 (dev_toggle_menu) : afficher / masquer le menu. F2 (dev_switch_team) : changer
## le camp du joueur (PlayerState) et centrer la caméra sur son QG.
## Absent des exports de production (builds non debug).

@export var simulation: UnitSimulation
@export var camera_rig: RTSCamera
## Facultatifs : changement de camp du joueur (F2) et centrage sur son QG.
@export var player: PlayerState
@export var buildings: BuildingSystem
## Menu visible au lancement (masqué par défaut quand un HUD occupe l'écran).
@export var start_visible: bool = true

@export_group("Troupes")
@export var plant_squads: Array[SquadData] = []
@export var zombie_squads: Array[SquadData] = []

@export_group("Placement")
## Distance (m) entre deux escouades voisines d'une même rangée.
@export var column_spacing: float = 12.0
## Distance (m) entre deux rangées d'escouades d'un même camp.
@export var row_spacing: float = 12.0
## Distance (m) entre le point visé et la première rangée de chaque camp.
@export var front_distance: float = 8.0
@export_range(1, 10) var squads_per_row: int = 5
## Écart minimal (m) entre l'emprise d'une nouvelle escouade et les escouades existantes.
@export var spawn_margin: float = 1.0
## Distance (m) maximale de recherche d'un emplacement libre.
@export var spawn_search_radius: float = 80.0

## Marge (pixels) entre le menu et les bords de l'écran.
@export var screen_margin: float = 12.0
## Décalage vertical (pixels) du menu : sous la barre de ressources (haut au centre),
## que le menu chevaucherait dans une fenêtre étroite.
@export var top_offset: float = 96.0
## Largeur (pixels) d'un bouton de troupe ; un nom plus long est abrégé (« … »).
@export var troop_button_width: float = 125.0


func _ready() -> void:
	if not OS.is_debug_build():
		queue_free()
		return
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_build_ui()
	visible = start_visible


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed(&"dev_toggle_menu"):
		visible = not visible
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed(&"dev_switch_team") and player != null:
		player.team = 1 - player.team
		var hq := buildings.get_headquarters(player.team) if buildings != null else null
		if hq != null:
			camera_rig.focus_on(hq.position)
		get_viewport().set_input_as_handled()


## Fait apparaître une escouade de chaque troupe autour du point visé par la caméra.
func spawn_all_troops() -> void:
	var center := camera_rig.global_position
	center.y = 0.0
	var space := FormationSpace.from_simulation(simulation, spawn_margin)
	_spawn_camp(plant_squads, 0, center, 1.0, PI, space)
	_spawn_camp(zombie_squads, 1, center, -1.0, 0.0, space)


## Fait apparaître une escouade de `data` du côté de son camp, près du point visé.
func spawn_squad(data: SquadData, team: int) -> Squad:
	var center := camera_rig.global_position
	center.y = 0.0
	var side := 1.0 if team == 0 else -1.0
	var facing := PI if team == 0 else 0.0
	var space := FormationSpace.from_simulation(simulation, spawn_margin)
	var half := Squad.footprint_half_extents(data, data.unit_count)
	var position := space.find_free(center + Vector3(0.0, 0.0, side * front_distance), half, facing,
			spawn_search_radius, 1.0, Vector3(0.0, 0.0, side))
	return simulation.spawn_squad(data, team, position, facing)


## Retire toutes les escouades (tous leurs membres).
func clear_all() -> void:
	for unit in simulation.units.duplicate():
		simulation.remove_unit(unit)


func _spawn_camp(squads: Array[SquadData], team: int, center: Vector3, side: float, facing: float,
		space: FormationSpace) -> void:
	var positions := SquadLayout.camp_positions(squads.size(), center, side, squads_per_row,
			column_spacing, row_spacing, front_distance)
	for i in squads.size():
		var half := Squad.footprint_half_extents(squads[i], squads[i].unit_count)
		var position := space.find_free(positions[i], half, facing, spawn_search_radius, 1.0,
				Vector3(0.0, 0.0, side))
		space.add(position, half, facing)
		simulation.spawn_squad(squads[i], team, position, facing)


func _build_ui() -> void:
	var panel := PanelContainer.new()
	panel.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT, Control.PRESET_MODE_MINSIZE, int(screen_margin))
	panel.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	panel.offset_top += top_offset
	panel.offset_bottom += top_offset
	add_child(panel)

	var content := VBoxContainer.new()
	panel.add_child(content)

	var title := Label.new()
	title.text = "DEV"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	content.add_child(title)

	var spawn_button := _make_button("Toutes les troupes",
			"Fait apparaître une escouade de chaque troupe autour du point visé.")
	spawn_button.pressed.connect(spawn_all_troops)
	content.add_child(spawn_button)

	_add_camp_buttons(content, "Plantes", plant_squads, 0)
	_add_camp_buttons(content, "Zombies", zombie_squads, 1)

	content.add_child(HSeparator.new())
	var clear_button := _make_button("Tout supprimer", "Retire toutes les escouades de la carte.")
	clear_button.pressed.connect(clear_all)
	content.add_child(clear_button)


## Titre du camp puis un bouton par troupe, sur deux colonnes.
func _add_camp_buttons(content: VBoxContainer, title: String, squads: Array[SquadData], team: int) -> void:
	content.add_child(HSeparator.new())
	var label := Label.new()
	label.text = title
	var faction := squads[0].unit_data.faction if not squads.is_empty() else null
	if faction != null:
		label.add_theme_color_override("font_color", faction.unit_color)
	content.add_child(label)
	var grid := GridContainer.new()
	grid.columns = 2
	content.add_child(grid)
	for data in squads:
		var unit := data.unit_data
		var button := _make_button(unit.display_name,
				"Fait apparaître une escouade de %s (%d) côté %s." % [unit.display_name, data.unit_count, title.to_lower()])
		button.custom_minimum_size.x = troop_button_width
		button.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		button.pressed.connect(spawn_squad.bind(data, team))
		grid.add_child(button)


func _make_button(text: String, tooltip: String) -> Button:
	var button := Button.new()
	button.text = text
	button.tooltip_text = tooltip
	# Pas de focus clavier : les touches restent à la caméra et aux raccourcis.
	button.focus_mode = Control.FOCUS_NONE
	return button
