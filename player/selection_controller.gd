class_name SelectionController
extends Node
## Sélection du joueur, par escouade :
## - clic sur une unité → son escouade entière ; clic dans le vide → désélection ;
## - glisser → toutes les escouades dont au moins une unité est dans le cadre.
## Le test se fait en espace écran (pas de collisionneurs sur les unités).

signal selection_changed(squads: Array[Squad])

@export var simulation: UnitSimulation
@export var camera_rig: RTSCamera
@export var selection_box: SelectionBox
## Camp contrôlé par ce joueur : seules ses escouades sont sélectionnables.
## -1 = tous les camps (scènes de test et débogage).
@export var team: int = 0

@export_group("Sélection")
## Distance (pixels) à partir de laquelle un clic devient un glisser.
@export var drag_threshold: float = 6.0
## Hauteur (m) du point visé sur une unité (environ le milieu du modèle).
@export var pick_height: float = 0.65
## Tolérance du clic, en multiple du rayon d'emprise visuelle de l'unité.
@export var pick_radius_scale: float = 1.3

var selected_squads: Array[Squad] = []

var _press_position: Vector2
var _is_pressing: bool = false
var _is_dragging: bool = false


func _ready() -> void:
	simulation.squad_destroyed.connect(_on_squad_destroyed)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var button := event as InputEventMouseButton
		if button.is_action_pressed("select"):
			_is_pressing = true
			_is_dragging = false
			_press_position = button.position
			get_viewport().set_input_as_handled()
		elif button.is_action_released("select") and _is_pressing:
			_is_pressing = false
			if _is_dragging:
				_select_in_rect(Rect2(_press_position, Vector2.ZERO).expand(button.position))
			else:
				_select_at(button.position)
			_is_dragging = false
			selection_box.hide_box()
			get_viewport().set_input_as_handled()
	elif event is InputEventMouseMotion and _is_pressing:
		var motion := event as InputEventMouseMotion
		if not _is_dragging and motion.position.distance_to(_press_position) > drag_threshold:
			_is_dragging = true
		if _is_dragging:
			selection_box.show_box(Rect2(_press_position, Vector2.ZERO).expand(motion.position))


func set_selection(squads: Array[Squad]) -> void:
	if squads == selected_squads:
		return
	selected_squads = squads
	selection_changed.emit(selected_squads)


func is_selected(squad: Squad) -> bool:
	return selected_squads.has(squad)


## Unité la plus proche du point écran, ou null. `only_team` < 0 : tous les camps.
func pick_unit(screen_position: Vector2, only_team: int = -1) -> Unit:
	var camera := camera_rig.get_camera()
	var camera_right := camera.global_basis.x
	var best: Unit = null
	var best_distance := INF
	for unit in simulation.units:
		if only_team >= 0 and unit.team != only_team:
			continue
		var world := unit.position + Vector3.UP * pick_height
		if camera.is_position_behind(world):
			continue
		var screen := camera.unproject_position(world)
		var edge := camera.unproject_position(world + camera_right * unit.data.footprint_radius * pick_radius_scale)
		var distance := screen.distance_to(screen_position)
		if distance <= screen.distance_to(edge) and distance < best_distance:
			best = unit
			best_distance = distance
	return best


func _select_at(screen_position: Vector2) -> void:
	var unit := pick_unit(screen_position, team)
	var squads: Array[Squad] = []
	if unit != null:
		squads.append(simulation.get_squad(unit.squad_id))
	set_selection(squads)


func _select_in_rect(rect: Rect2) -> void:
	var camera := camera_rig.get_camera()
	var squads: Array[Squad] = []
	for squad in simulation.squads:
		if team >= 0 and squad.team != team:
			continue
		for unit in squad.units:
			var world := unit.position + Vector3.UP * pick_height
			if not camera.is_position_behind(world) and rect.has_point(camera.unproject_position(world)):
				squads.append(squad)
				break
	set_selection(squads)


## Une escouade détruite quitte la sélection.
func _on_squad_destroyed(squad: Squad) -> void:
	if selected_squads.has(squad):
		var remaining: Array[Squad] = []
		for selected in selected_squads:
			if selected != squad:
				remaining.append(selected)
		set_selection(remaining)
