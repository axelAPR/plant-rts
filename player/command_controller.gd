class_name CommandController
extends Node
## Ordres du joueur, au clic droit :
## - escouades sélectionnées : sur une unité ennemie → attaque de son escouade ; sur
##   le terrain → déplacement ;
## - bâtiment sélectionné (du camp de la sélection) : point de ralliement.

@export var selection: SelectionController
@export var order_system: OrderSystem
@export var camera_rig: RTSCamera
## Facultatif : bâtiments (point de ralliement).
@export var buildings: BuildingSystem
## Couches physiques considérées comme terrain pour viser un point au sol.
@export_flags_3d_physics var ground_mask: int = 1
@export var ray_length: float = 1000.0


func _unhandled_input(event: InputEvent) -> void:
	if not (event is InputEventMouseButton and event.is_action_pressed("command")):
		return
	var screen_position := (event as InputEventMouseButton).position
	var building := selection.selected_building
	if building != null and buildings != null and (selection.team < 0 or building.team == selection.team):
		var ground := _raycast_ground(screen_position)
		if not ground.is_empty():
			buildings.set_rally_point(building, ground.position)
			get_viewport().set_input_as_handled()
		return
	if selection.selected_squads.is_empty():
		return
	var enemy := _pick_enemy(screen_position)
	if enemy != null:
		order_system.issue_attack(selection.selected_squads, order_system.simulation.get_squad(enemy.squad_id))
		get_viewport().set_input_as_handled()
		return
	var hit := _raycast_ground(screen_position)
	if hit.is_empty():
		return
	order_system.issue_move(selection.selected_squads, hit.position)
	get_viewport().set_input_as_handled()


## Point du terrain sous le curseur ; dictionnaire vide si rien n'est touché.
func _raycast_ground(screen_position: Vector2) -> Dictionary:
	var camera := camera_rig.get_camera()
	var from := camera.project_ray_origin(screen_position)
	var to := from + camera.project_ray_normal(screen_position) * ray_length
	var query := PhysicsRayQueryParameters3D.create(from, to, ground_mask)
	return camera.get_world_3d().direct_space_state.intersect_ray(query)


## Unité ennemie (d'un camp autre que celui des escouades sélectionnées) sous le
## curseur, ou null.
func _pick_enemy(screen_position: Vector2) -> Unit:
	var unit := selection.pick_unit(screen_position)
	if unit == null:
		return null
	for squad in selection.selected_squads:
		if squad.team != unit.team:
			return unit
	return null
