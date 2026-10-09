class_name SelectionController
extends Node
## Sélection du joueur, par escouade ou par bâtiment (jamais les deux à la fois) :
## - clic sur une unité → son escouade entière ;
## - sinon, clic sur un bâtiment → ce bâtiment (rayon de la caméra contre les volumes
##   de clic de BuildingRenderer, couche `building_pick_mask`) ;
## - clic dans le vide → désélection ;
## - glisser → toutes les escouades dont au moins une unité est dans le cadre.
## Les unités sont testées en espace écran (pas de collisionneurs sur les unités).

signal selection_changed(squads: Array[Squad])
## Bâtiment sélectionné (null : aucun).
signal selected_building_changed(building: Building)

@export var simulation: UnitSimulation
@export var camera_rig: RTSCamera
@export var selection_box: SelectionBox
## Facultatif : bâtiments sélectionnables.
@export var buildings: BuildingSystem
## Couches physiques des volumes de clic des bâtiments.
@export_flags_3d_physics var building_pick_mask: int = 2
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
var selected_building: Building = null

const _NONE: Array[Squad] = []

var _press_position: Vector2
var _is_pressing: bool = false
var _is_dragging: bool = false


func _ready() -> void:
	simulation.squad_destroyed.connect(_on_squad_destroyed)
	if buildings != null:
		buildings.building_destroyed.connect(_on_building_destroyed)


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
	if not squads.is_empty():
		_set_building(null)
	if squads == selected_squads:
		return
	selected_squads = squads
	selection_changed.emit(selected_squads)


## Sélectionne un bâtiment (désélectionne les escouades) ; null : rien.
func set_building_selection(building: Building) -> void:
	if building != null:
		set_selection(_NONE.duplicate())
	_set_building(building)


## Désélectionne tout.
func clear_selection() -> void:
	set_selection(_NONE.duplicate())
	_set_building(null)


func _set_building(building: Building) -> void:
	if building == selected_building:
		return
	selected_building = building
	selected_building_changed.emit(selected_building)


## Bâtiment vivant sous le point écran (rayon de la caméra), ou null.
## `only_team` < 0 : tous les camps.
func pick_building(screen_position: Vector2, only_team: int = -1) -> Building:
	if buildings == null:
		return null
	var camera := camera_rig.get_camera()
	var from := camera.project_ray_origin(screen_position)
	var to := from + camera.project_ray_normal(screen_position) * 2000.0
	var query := PhysicsRayQueryParameters3D.create(from, to, building_pick_mask)
	var hit := camera.get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty() or not (hit.collider as Object).has_meta(BuildingRenderer.BUILDING_ID_META):
		return null
	var building := buildings.get_building((hit.collider as Object).get_meta(BuildingRenderer.BUILDING_ID_META))
	if building == null or not building.is_alive() or (only_team >= 0 and building.team != only_team):
		return null
	return building


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
	if unit != null:
		var squads: Array[Squad] = [simulation.get_squad(unit.squad_id)]
		set_selection(squads)
		return
	var building := pick_building(screen_position, team)
	if building != null:
		set_building_selection(building)
	else:
		clear_selection()


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
	if squads.is_empty():
		clear_selection()
	else:
		set_selection(squads)


## Un bâtiment détruit quitte la sélection.
func _on_building_destroyed(building: Building) -> void:
	if building == selected_building:
		_set_building(null)


## Une escouade détruite quitte la sélection.
func _on_squad_destroyed(squad: Squad) -> void:
	if selected_squads.has(squad):
		var remaining: Array[Squad] = []
		for selected in selected_squads:
			if selected != squad:
				remaining.append(selected)
		set_selection(remaining)
