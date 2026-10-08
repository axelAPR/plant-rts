extends SceneTree
## Test automatisé de toutes les troupes : charge all_troops_test.tscn (une escouade
## par troupe, plantes et zombies), vérifie les effectifs, l'absence de superposition
## à l'arrêt, puis déplace toutes les escouades simultanément et contrôle la marche
## en formation et l'arrivée.
##
## Lancement : Godot --headless --path . --script res://tests/squad_test/all_troops_runner.gd
## Option : -- --screenshots=<dossier absolu> pour enregistrer des captures PNG (lancer
## alors sans --headless). En fenêtré, la vraie souris peut se mêler aux clics simulés
## et fausser des vérifications de sélection : ne pas toucher la souris pendant le test.
## Code de sortie : 0 si tout passe, 1 sinon.

const SCENE_PATH := "res://tests/squad_test/all_troops_test.tscn"
const MOVE_TIMEOUT := 30.0
## Distance (m) parcourue par chaque escouade, en s'éloignant du camp adverse.
const MOVE_DISTANCE := 5.0
const POSITION_TOLERANCE := 0.6
const MAX_TRAVEL_FORMATION_ERROR := 3.0
const REST_FORMATION_ERROR := 0.3
## Tolérance (m) sur la distance minimale entre deux unités (somme de leurs rayons).
const OVERLAP_TOLERANCE := 0.02

var _simulation: UnitSimulation
var _orders: OrderSystem
var _screenshot_dir: String = ""
var _failures: Array[String] = []
var _checks: int = 0


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--screenshots="):
			_screenshot_dir = arg.trim_prefix("--screenshots=")
	_run.call_deferred()


func _run() -> void:
	var scene: Node3D = (load(SCENE_PATH) as PackedScene).instantiate()
	root.add_child(scene)
	_simulation = scene.get_node("UnitSimulation")
	_orders = scene.get_node("OrderSystem")
	var camera_rig: RTSCamera = scene.get_node("RTSCamera")
	camera_rig.edge_scroll_enabled = false
	await _frames(30)

	# 1. Effectifs
	var expected := (scene.plant_squads as Array).size() + (scene.zombie_squads as Array).size()
	_check(_simulation.squads.size() == expected, "%d escouades créées (attendu %d)" % [_simulation.squads.size(), expected])
	for squad in _simulation.squads:
		var data := squad.data
		_check(squad.units.size() == data.unit_count,
				"%s (camp %d) : %d unités (attendu %d)" % [data.unit_data.id, squad.team, squad.units.size(), data.unit_count])

	# 2. Aucune superposition à l'arrêt, formations en place
	await _wait_physics(60)
	var rest := _min_clearance()
	_check(rest.clearance >= -OVERLAP_TOLERANCE, "aucune superposition à l'arrêt (marge min %.3f m, %s)" % [rest.clearance, rest.pair])
	for squad in _simulation.squads:
		_check(squad.get_formation_error() < REST_FORMATION_ERROR,
				"%s : formation en place au repos (écart %.2f m)" % [squad.data.unit_data.id, squad.get_formation_error()])
	await _screenshot("all_01_depart")

	# 3. Sélection (souris simulée) : plantes et zombies sont sélectionnables dans cette scène
	var selection: SelectionController = scene.get_node("SelectionController")
	var camera := camera_rig.get_camera()
	for squad in _simulation.squads:
		var unit := squad.units[0]
		await _click(camera.unproject_position(unit.position + Vector3.UP * selection.pick_height))
		_check(selection.selected_squads == [squad],
				"clic sur %s (camp %d) → son escouade" % [squad.data.unit_data.id, squad.team])
	var zombie_squads: Array[Squad] = _simulation.squads.filter(func(s: Squad) -> bool: return s.team == 1)
	var lo := Vector3(INF, 0.0, INF)
	var hi := Vector3(-INF, 0.0, -INF)
	for squad in zombie_squads:
		for unit in squad.units:
			lo = Vector3(minf(lo.x, unit.position.x), 0.0, minf(lo.z, unit.position.z))
			hi = Vector3(maxf(hi.x, unit.position.x), 0.0, maxf(hi.z, unit.position.z))
	var rect := Rect2(camera.unproject_position(lo + Vector3(-2, 0, -2)), Vector2.ZERO).expand(camera.unproject_position(hi + Vector3(2, 0, 2)))
	rect = rect.expand(camera.unproject_position(Vector3(lo.x - 2, 0, hi.z + 2))).expand(camera.unproject_position(Vector3(hi.x + 2, 0, lo.z - 2)))
	await _drag(rect.position, rect.end)
	var all_zombies := selection.selected_squads.size() == zombie_squads.size() \
			and selection.selected_squads.all(func(s: Squad) -> bool: return s.team == 1)
	_check(all_zombies, "glisser sur le camp zombie → %d escouades zombies (attendu %d)" % [selection.selected_squads.size(), zombie_squads.size()])
	await _screenshot("all_01b_selection_zombies")
	await _click(camera.unproject_position(Vector3(0, 0, 0)))

	# 3. Déplacement simultané de toutes les escouades, chacune vers l'arrière de son camp
	var targets: Dictionary[Squad, Vector3] = {}
	for squad in _simulation.squads:
		var away := 1.0 if squad.team == 0 else -1.0
		var target := squad.get_center() + Vector3(0.0, 0.0, away * MOVE_DISTANCE)
		var group: Array[Squad] = [squad]
		_orders.issue_move(group, target)
		targets[squad] = (squad.order as MoveOrder).target

	# Mesures dès le premier tick : le demi-tour initial est la phase la plus délicate.
	var max_error: Dictionary[Squad, float] = {}
	var min_clear := INF
	var worst_pair := ""
	var elapsed := 0.0
	var ticks := 0
	while elapsed < MOVE_TIMEOUT:
		await physics_frame
		ticks += 1
		elapsed += 1.0 / Engine.physics_ticks_per_second
		if ticks == 40:
			await _screenshot("all_02_deplacement")
		var clear := _min_clearance()
		if clear.clearance < min_clear:
			min_clear = clear.clearance
			worst_pair = clear.pair
		var moving := false
		for squad in _simulation.squads:
			if squad.order != null:
				moving = true
				max_error[squad] = maxf(max_error.get(squad, 0.0), squad.get_formation_error())
		if not moving:
			break
	_check(elapsed < MOVE_TIMEOUT, "toutes les escouades sont arrivées (%.1f s)" % elapsed)
	_check(min_clear >= -OVERLAP_TOLERANCE, "aucune superposition pendant la marche (marge min %.3f m, %s)" % [min_clear, worst_pair])
	for squad in _simulation.squads:
		var id := squad.data.unit_data.id
		_check(max_error.get(squad, 0.0) < MAX_TRAVEL_FORMATION_ERROR,
				"%s : formation cohérente en marche (écart max %.2f m)" % [id, max_error.get(squad, 0.0)])
		var offset := squad.get_center() - targets[squad]
		offset.y = 0.0
		_check(offset.length() < POSITION_TOLERANCE, "%s : arrivé à destination (écart %.2f m)" % [id, offset.length()])
		_check(squad.get_formation_error() < REST_FORMATION_ERROR,
				"%s : reformé à l'arrivée (écart %.2f m)" % [id, squad.get_formation_error()])
	await _screenshot("all_03_arrivee")

	print("\n%d vérifications, %d échec(s)" % [_checks, _failures.size()])
	quit(0 if _failures.is_empty() else 1)


## Plus petite marge entre deux unités : distance au sol moins la somme des rayons.
func _min_clearance() -> Dictionary:
	var units := _simulation.units
	var best := INF
	var pair := ""
	for i in units.size():
		for j in range(i + 1, units.size()):
			var offset := units[i].position - units[j].position
			offset.y = 0.0
			var clearance := offset.length() - units[i].data.radius - units[j].data.radius
			if clearance < best:
				best = clearance
				pair = "%s/%s" % [units[i].data.id, units[j].data.id]
	return {"clearance": best, "pair": pair}


func _click(position: Vector2) -> void:
	_mouse_button(true, position)
	await _frames(2)
	_mouse_button(false, position)
	await _frames(2)


func _drag(from: Vector2, to: Vector2) -> void:
	_mouse_button(true, from)
	for i in range(1, 11):
		var motion := InputEventMouseMotion.new()
		motion.position = from.lerp(to, i / 10.0)
		motion.button_mask = MOUSE_BUTTON_MASK_LEFT
		root.push_input(motion, true)
		await _frames(1)
	_mouse_button(false, to)
	await _frames(2)


func _mouse_button(pressed: bool, position: Vector2) -> void:
	var event := InputEventMouseButton.new()
	event.button_index = MOUSE_BUTTON_LEFT
	event.pressed = pressed
	event.position = position
	root.push_input(event, true)


func _wait_physics(count: int) -> void:
	for i in count:
		await physics_frame


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
	root.get_texture().get_image().save_png(_screenshot_dir.path_join(name + ".png"))
