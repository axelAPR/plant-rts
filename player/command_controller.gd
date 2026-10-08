class_name CommandController
extends Node
## Ordres du joueur : clic droit sur le terrain → déplacement des escouades sélectionnées.

@export var selection: SelectionController
@export var order_system: OrderSystem
@export var camera_rig: RTSCamera
## Couches physiques considérées comme terrain pour viser un point au sol.
@export_flags_3d_physics var ground_mask: int = 1
@export var ray_length: float = 1000.0


func _unhandled_input(event: InputEvent) -> void:
	if not (event is InputEventMouseButton and event.is_action_pressed("command")):
		return
	if selection.selected_squads.is_empty():
		return
	var hit := _raycast_ground((event as InputEventMouseButton).position)
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
