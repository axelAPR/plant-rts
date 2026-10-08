extends SceneTree
## Test automatisé du prototype d'escouades : charge squad_test.tscn, simule les
## entrées souris (clic, glisser, clic droit) et vérifie sélection, déplacement,
## absence de superposition et cohésion des formations.
##
## Lancement (fenêtré, nécessaire pour les captures) :
##   Godot --path . --script res://tests/squad_test/squad_test_runner.gd
## Option : -- --screenshots=<dossier absolu> pour enregistrer des captures PNG.
## Code de sortie : 0 si tout passe, 1 sinon.

const SCENE_PATH := "res://tests/squad_test/squad_test.tscn"
## Délai maximal (s) pour qu'un déplacement se termine.
const MOVE_TIMEOUT := 20.0
## Tolérance (m) sur la position finale d'une escouade.
const POSITION_TOLERANCE := 0.6
## Écart (m) unité/emplacement maximal toléré pendant la marche.
const MAX_TRAVEL_FORMATION_ERROR := 2.5

var _scene: Node3D
var _simulation: UnitSimulation
var _selection: SelectionController
var _camera: Camera3D
var _screenshot_dir: String = ""
var _failures: Array[String] = []
var _checks: int = 0


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--screenshots="):
			_screenshot_dir = arg.trim_prefix("--screenshots=")
	_run.call_deferred()


func _run() -> void:
	_scene = (load(SCENE_PATH) as PackedScene).instantiate()
	root.add_child(_scene)
	_simulation = _scene.get_node("UnitSimulation")
	_selection = _scene.get_node("SelectionController")
	var camera_rig: RTSCamera = _scene.get_node("RTSCamera")
	camera_rig.edge_scroll_enabled = false
	_camera = camera_rig.get_camera()
	await _frames(30)

	var squad_a := _simulation.squads[0]
	var squad_b := _simulation.squads[1]
	_check(_simulation.squads.size() == 2, "2 escouades créées")
	_check(squad_a.units.size() == 6 and squad_b.units.size() == 6, "6 unités par escouade")
	_check(_min_unit_distance() >= 1.1 - 0.01, "aucune superposition au départ")
	await _screenshot("01_depart")

	# 1. Clic sur une unité → toute son escouade est sélectionnée.
	await _click(_screen_of(squad_a.units[4].position + Vector3.UP * 0.65))
	_check(_selection.selected_squads == [squad_a], "clic sur une unité → son escouade")
	await _screenshot("02_selection_escouade_1")

	# Clic dans le vide → désélection.
	await _click(_screen_of(Vector3(0.0, 0.0, 8.0)))
	_check(_selection.selected_squads.is_empty(), "clic dans le vide → désélection")

	# 2. Glisser couvrant les deux escouades → les deux sont sélectionnées.
	await _drag(_screen_of(Vector3(-9.0, 0.0, -3.0)), _screen_of(Vector3(9.0, 0.0, 3.0)))
	_check(_selection.selected_squads.size() == 2, "glisser → deux escouades sélectionnées")
	await _screenshot("03_selection_deux_escouades")

	# Glisser ne couvrant qu'une escouade → seulement celle-ci.
	await _drag(_screen_of(Vector3(1.0, 0.0, -3.0)), _screen_of(Vector3(8.0, 0.0, 3.0)))
	_check(_selection.selected_squads == [squad_b], "glisser partiel → une seule escouade")

	# 3. Déplacer une escouade.
	await _click(_screen_of(squad_a.units[0].position + Vector3.UP * 0.65))
	var target_a := Vector3(-6.0, 0.0, -10.0)
	var b_before := squad_b.get_center()
	await _right_click(_screen_of(target_a))
	_check(squad_a.order is MoveOrder and squad_b.order == null, "ordre donné à l'escouade sélectionnée seulement")
	await _frames(20)
	await _screenshot("04_deplacement_escouade_1")
	var stats := await _wait_until_idle([squad_a])
	_check(squad_a.get_center().distance_to(target_a) < POSITION_TOLERANCE,
			"escouade 1 arrivée à destination (écart %.2f m)" % squad_a.get_center().distance_to(target_a))
	_check(squad_b.get_center().distance_to(b_before) < 0.05, "escouade 2 restée immobile")
	_check_travel(stats, "déplacement d'une escouade")
	await _screenshot("05_arrivee_escouade_1")

	# 4. Déplacer les deux escouades ensemble, vers un point situé derrière elles
	#    (demi-tour complet de la formation).
	await _drag(_screen_of(Vector3(-12.0, 0.0, -14.0)), _screen_of(Vector3(9.0, 0.0, 3.0)))
	_check(_selection.selected_squads.size() == 2, "re-sélection des deux escouades")
	var target_group := Vector3(2.0, 0.0, 6.0)
	await _right_click(_screen_of(target_group))
	_check(squad_a.order is MoveOrder and squad_b.order is MoveOrder, "ordre de groupe donné aux deux escouades")
	var dest_a := (squad_a.order as MoveOrder).target
	var dest_b := (squad_b.order as MoveOrder).target
	var min_gap := (squad_a.get_formation_width() + squad_b.get_formation_width()) * 0.5
	_check(dest_a.distance_to(dest_b) >= min_gap, "destinations distinctes, côte à côte")
	await _frames(45)
	await _screenshot("06_deplacement_deux_escouades")
	stats = await _wait_until_idle([squad_a, squad_b])
	_check_travel(stats, "déplacement de groupe")

	# 5. Formations cohérentes et non fusionnées à l'arrivée.
	for squad in [squad_a, squad_b]:
		_check(squad.get_formation_error() < 0.3, "escouade %d reformée (écart %.2f m)" % [squad.id + 1, squad.get_formation_error()])
	_check(_squads_separated(squad_a, squad_b), "chaque unité est plus proche du centre de sa propre escouade")
	await _screenshot("07_arrivee_deux_escouades")

	_finish()


# --- Simulation des entrées -------------------------------------------------

func _click(position: Vector2) -> void:
	_mouse_button(MOUSE_BUTTON_LEFT, true, position)
	await _frames(2)
	_mouse_button(MOUSE_BUTTON_LEFT, false, position)
	await _frames(2)


func _right_click(position: Vector2) -> void:
	_mouse_button(MOUSE_BUTTON_RIGHT, true, position)
	await _frames(2)
	_mouse_button(MOUSE_BUTTON_RIGHT, false, position)
	await _frames(2)


func _drag(from: Vector2, to: Vector2) -> void:
	_mouse_button(MOUSE_BUTTON_LEFT, true, from)
	for i in range(1, 11):
		var motion := InputEventMouseMotion.new()
		motion.position = from.lerp(to, i / 10.0)
		motion.button_mask = MOUSE_BUTTON_MASK_LEFT
		root.push_input(motion, true)
		await _frames(1)
	_mouse_button(MOUSE_BUTTON_LEFT, false, to)
	await _frames(2)


func _mouse_button(button: MouseButton, pressed: bool, position: Vector2) -> void:
	var event := InputEventMouseButton.new()
	event.button_index = button
	event.pressed = pressed
	event.position = position
	root.push_input(event, true)


# --- Mesures ----------------------------------------------------------------

## Attend la fin des ordres en mesurant, à chaque tick, l'écart de formation maximal
## et la distance minimale entre unités.
func _wait_until_idle(squads: Array[Squad]) -> Dictionary:
	var max_error := 0.0
	var min_distance := INF
	var elapsed := 0.0
	while elapsed < MOVE_TIMEOUT:
		await physics_frame
		elapsed += 1.0 / Engine.physics_ticks_per_second
		min_distance = minf(min_distance, _min_unit_distance())
		var any_moving := false
		for squad in squads:
			if squad.order != null:
				any_moving = true
				max_error = maxf(max_error, squad.get_formation_error())
		if not any_moving:
			break
	return {"timeout": elapsed >= MOVE_TIMEOUT, "time": elapsed, "max_error": max_error, "min_distance": min_distance}


func _check_travel(stats: Dictionary, label: String) -> void:
	_check(not stats.timeout, "%s terminé en %.1f s" % [label, stats.time])
	_check(stats.max_error < MAX_TRAVEL_FORMATION_ERROR,
			"%s : formation cohérente (écart max %.2f m)" % [label, stats.max_error])
	_check(stats.min_distance >= 1.1 - 0.02,
			"%s : aucune superposition (distance min %.2f m)" % [label, stats.min_distance])


func _min_unit_distance() -> float:
	var result := INF
	var units := _simulation.units
	for i in units.size():
		for j in range(i + 1, units.size()):
			var offset := units[i].position - units[j].position
			offset.y = 0.0
			result = minf(result, offset.length())
	return result


func _squads_separated(a: Squad, b: Squad) -> bool:
	var center_a := a.get_center()
	var center_b := b.get_center()
	for unit in a.units:
		if unit.position.distance_to(center_a) >= unit.position.distance_to(center_b):
			return false
	for unit in b.units:
		if unit.position.distance_to(center_b) >= unit.position.distance_to(center_a):
			return false
	return true


# --- Utilitaires ------------------------------------------------------------

func _screen_of(world: Vector3) -> Vector2:
	return _camera.unproject_position(world)


func _frames(count: int) -> void:
	for i in count:
		await process_frame


func _check(condition: bool, label: String) -> void:
	_checks += 1
	print(("  OK    " if condition else "  ÉCHEC ") + label)
	if not condition:
		_failures.append(label)


func _screenshot(name: String) -> void:
	if _screenshot_dir.is_empty():
		return
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	image.save_png(_screenshot_dir.path_join(name + ".png"))


func _finish() -> void:
	print("\n%d vérifications, %d échec(s)" % [_checks, _failures.size()])
	quit(0 if _failures.is_empty() else 1)
