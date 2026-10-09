extends SceneTree
## Captures du HUD et des QG en situation (fenêtré, pour le rendu) : Arbre de Vie
## sélectionné avec un Maïs en production, Tombeau sélectionné, vue rapprochée de
## chaque QG, vue d'ensemble avec la mini-carte.
##
## Lancement : Godot --path . --script res://tests/hud_test/hud_capture.gd
## Les PNG sont écrits dans tests/hud_test/captures/.

const MAP := "res://world/maps/suburb/suburb.tscn"
const OUT := "res://tests/hud_test/captures/"


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT))
	var scene := (load(MAP) as PackedScene).instantiate()
	root.add_child(scene)
	var buildings: BuildingSystem = scene.get_node("BuildingSystem")
	var selection: SelectionController = scene.get_node("SelectionController")
	var camera: RTSCamera = scene.get_node("RTSCamera")
	var player: PlayerState = scene.get_node("PlayerState")
	var hud: RtsHud = scene.get_node("HUD/RtsHud")
	await _frames(10)
	var tree := buildings.get_headquarters(0)
	var tomb := buildings.get_headquarters(1)

	selection.set_building_selection(tree)
	await _frames(2)
	hud.command_panel.trigger(0)
	buildings.step(7.0)
	await _view(camera, tree.position + Vector3(0, 0, -8), 46.0, "tree_selected")
	await _view(camera, tree.position + Vector3(0, 0, -4), 18.0, "tree_close")

	player.team = 1
	selection.set_building_selection(tomb)
	await _frames(2)
	hud.command_panel.trigger(0)
	buildings.step(4.0)
	await _view(camera, tomb.position + Vector3(0, 0, 8), 46.0, "tomb_selected")
	await _view(camera, tomb.position + Vector3(0, 0, 4), 18.0, "tomb_close")
	quit()


func _view(camera: RTSCamera, target: Vector3, distance: float, tag: String) -> void:
	camera.focus_on(target)
	camera.zoom_by((distance / 40.0) - 1.0)
	await _frames(150)
	var path := OUT + "hud_%s.png" % tag
	root.get_viewport().get_texture().get_image().save_png(ProjectSettings.globalize_path(path))
	print("capture : %s" % path)
	camera.zoom_by((40.0 / distance) - 1.0)


func _frames(count: int) -> void:
	for i in count:
		await process_frame
