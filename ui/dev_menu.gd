class_name DevMenu
extends Control
## Menu de développement, en haut à droite de l'écran.
## Le bouton fait apparaître une escouade de chaque troupe autour du point visé par
## la caméra : plantes (camp 0) au sud, zombies (camp 1) au nord, face à face. Chaque
## escouade prend l'emplacement libre le plus proche : pas d'apparition par-dessus
## des escouades existantes.
## Absent des exports de production (builds non debug).

@export var simulation: UnitSimulation
@export var camera_rig: RTSCamera

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


func _ready() -> void:
	if not OS.is_debug_build():
		queue_free()
		return
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_build_ui()


## Fait apparaître une escouade de chaque troupe autour du point visé par la caméra.
func spawn_all_troops() -> void:
	var center := camera_rig.global_position
	center.y = 0.0
	var space := FormationSpace.from_simulation(simulation, spawn_margin)
	_spawn_camp(plant_squads, 0, center, 1.0, PI, space)
	_spawn_camp(zombie_squads, 1, center, -1.0, 0.0, space)


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
	add_child(panel)

	var content := VBoxContainer.new()
	panel.add_child(content)

	var title := Label.new()
	title.text = "DEV"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	content.add_child(title)

	var spawn_button := Button.new()
	spawn_button.text = "Toutes les troupes"
	spawn_button.tooltip_text = "Fait apparaître une escouade de chaque troupe autour du point visé."
	# Pas de focus clavier : les touches restent à la caméra et aux raccourcis.
	spawn_button.focus_mode = Control.FOCUS_NONE
	spawn_button.pressed.connect(spawn_all_troops)
	content.add_child(spawn_button)
