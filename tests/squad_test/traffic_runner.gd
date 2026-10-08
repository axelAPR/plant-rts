extends SceneTree
## Test automatisé des blocages entre escouades (trafic). Sans scène ni rendu : la
## simulation est avancée tick par tick (UnitSimulation.step), ce qui rend les
## scénarios rapides et reproductibles.
##
## Scénarios :
##   a. deux escouades alliées qui se croisent de face ;
##   b. une escouade qui traverse une escouade alliée à l'arrêt ;
##   c. 20 escouades envoyées ensemble sur un même point (ordre de groupe) ;
##   d. deux ordres séparés qui visent le même point ;
##   e. charge : ~150 escouades de troupes variées, ordre de groupe à travers la carte ;
##   e2. charge réaliste : 9 fois « Toutes les troupes » au même endroit, superposées
##       (comportement de l'ancien menu DEV : 153 escouades, plantes et zombies), puis
##       un ordre de groupe ;
##   f. une escouade face à un mur d'escouades ennemies à l'arrêt : elle doit s'arrêter
##      proprement (détection de blocage) ;
##   g. une escouade envoyée sur une escouade alliée à l'arrêt (superposition).
## Critères communs : tous les ordres se terminent dans le délai, aucune superposition
## entre unités à l'arrêt, aucune unité qui court encore une fois tout arrêté, et
## formations reformées à l'arrivée (sauf escouades superposées : d et g).
##
## Lancement : Godot --headless --path . --script res://tests/squad_test/traffic_runner.gd
## Options (après --) :
##   --only=a,c                  ne lance que certains scénarios ;
##   --screenshots=<dossier>     captures des tests de charge (départ, en route,
##                               arrivée) ; nécessite une fenêtre (sans --headless).
## Code de sortie : 0 si tout passe, 1 sinon.

const TICK := 1.0 / 60.0
## Durée (s) simulée après la fin des ordres pour vérifier l'état au repos.
const SETTLE_TIME := 3.0
## Vitesse (m/s) au-delà de laquelle une unité au repos « court dans le vide ».
const REST_SPEED := 0.15
## Tolérance (m) sur la marge entre deux unités (distance moins la somme des rayons).
const OVERLAP_TOLERANCE := 0.02
## Écart unité/emplacement (m) maximal pour une formation reformée.
const REST_FORMATION_ERROR := 0.3
## Écart (m) toléré entre le centre d'une escouade et sa destination, quand celle-ci est libre.
const POSITION_TOLERANCE := 0.6
## Marge de délai : un ordre doit finir en moins de (distance / vitesse) × ce facteur + TIME_MARGIN.
const TIME_FACTOR := 2.0
const TIME_MARGIN := 10.0
## Instant (s simulées) de la capture « en route » des tests de charge.
const MID_SHOT_TIME := 20.0

const SQUAD_DIR := "res://data/units/"
const ALL_SQUADS: Array[String] = [
	"peashooter", "sunflower", "kernel_corn", "cactus", "rose", "chomper", "citron", "torchwood",
	"browncoat", "foot_soldier", "engineer", "scientist", "deadbeard", "all_star",
	"super_brainz", "action_hero_80s", "z_mech",
]

var _simulation: UnitSimulation
var _orders: OrderSystem
## Décor de rendu (captures uniquement) : sol, lumière, caméra, affichage des unités.
var _world: Node3D
var _camera: Camera3D
var _screenshot_dir: String = ""
## Nombre d'escouades arrêtées sur blocage lors du dernier _run_until_idle.
var _last_stalled: int = 0
var _failures: Array[String] = []
var _checks: int = 0


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	var only := PackedStringArray()
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--only="):
			only = arg.trim_prefix("--only=").split(",")
		elif arg.begins_with("--screenshots="):
			_screenshot_dir = arg.trim_prefix("--screenshots=")
	var scenarios: Array[Array] = [
		["a", "croisement de face", _scenario_head_on],
		["b", "traversée d'une escouade à l'arrêt", _scenario_cross_idle],
		["c", "20 escouades vers un même point", _scenario_group_of_20],
		["d", "deux ordres séparés vers le même point", _scenario_same_point],
		["e", "charge : 150 escouades à travers la carte", _scenario_load],
		["e2", "charge réaliste : 9 × toutes les troupes superposées", _scenario_stacked_load],
		["f", "mur d'escouades ennemies", _scenario_enemy_wall],
		["g", "escouade envoyée sur une escouade à l'arrêt", _scenario_onto_idle],
	]
	for scenario in scenarios:
		if only.is_empty() or only.has(scenario[0]):
			print("\n== %s. %s" % [scenario[0], scenario[1]])
			_reset(not _screenshot_dir.is_empty() and scenario[0] in ["e", "e2"])
			await (scenario[2] as Callable).call()
	print("\n%d vérifications, %d échec(s)" % [_checks, _failures.size()])
	quit(0 if _failures.is_empty() else 1)


# --- Scénarios ---------------------------------------------------------------

func _scenario_head_on() -> void:
	for id in ["peashooter", "browncoat", "deadbeard", "z_mech"]:
		print("  -- %s contre %s" % [id, id])
		_reset()
		# Destinations au-delà du point de départ de l'autre escouade : libres, et les
		# trajectoires se croisent de face.
		var data := _squad_data(id)
		var a := _simulation.spawn_squad(data, 0, Vector3(0.0, 0.0, -12.0), 0.0)
		var b := _simulation.spawn_squad(data, 0, Vector3(0.0, 0.0, 12.0), PI)
		_move([a], Vector3(0.0, 0.0, 20.0))
		_move([b], Vector3(0.0, 0.0, -20.0))
		await _run_until_idle([a, b], true)


func _scenario_cross_idle() -> void:
	var idle := _simulation.spawn_squad(_squad_data("peashooter"), 0, Vector3.ZERO, 0.0)
	var mover := _simulation.spawn_squad(_squad_data("peashooter"), 0, Vector3(0.0, 0.0, -14.0), 0.0)
	var idle_start := idle.get_center()
	_move([mover], Vector3(0.0, 0.0, 14.0))
	await _run_until_idle([mover], true)
	var drift := idle.get_center().distance_to(idle_start)
	print("  info  escouade à l'arrêt déplacée de %.2f m" % drift)


func _scenario_group_of_20() -> void:
	var squads := _spawn_grid(20, 5, Vector3(0.0, 0.0, -30.0), 12.0, 0)
	_move(squads, Vector3(0.0, 0.0, 30.0))
	await _run_until_idle(squads, false)


func _scenario_same_point() -> void:
	var data := _squad_data("peashooter")
	var a := _simulation.spawn_squad(data, 0, Vector3(-14.0, 0.0, -10.0), 0.0)
	var b := _simulation.spawn_squad(data, 0, Vector3(14.0, 0.0, -10.0), 0.0)
	var point := Vector3(0.0, 0.0, 10.0)
	_move([a], point)
	_move([b], point)
	_check((a.order as MoveOrder).target == (b.order as MoveOrder).target,
			"superposition autorisée : même destination pour les deux ordres")
	await _run_until_idle([a, b], false, "", false)


func _scenario_load() -> void:
	var squads := _spawn_grid(150, 15, Vector3(0.0, 0.0, -70.0), 11.0, 0)
	_move(squads, Vector3(0.0, 0.0, 70.0))
	await _run_until_idle(squads, false, "e")


## Reproduit le pire cas de l'ancien menu DEV (9 clics sans bouger la caméra) : les
## escouades apparaissent les unes sur les autres. Puis un seul ordre de groupe.
func _scenario_stacked_load() -> void:
	for i in 9:
		for id in ALL_SQUADS.size():
			var plant := id < 8
			var count := 8 if plant else ALL_SQUADS.size() - 8
			var positions := SquadLayout.camp_positions(count, Vector3.ZERO, 1.0 if plant else -1.0, 5, 12.0, 12.0, 8.0)
			_simulation.spawn_squad(_squad_data(ALL_SQUADS[id]), 0 if plant else 1,
					positions[id if plant else id - 8], PI if plant else 0.0)
	# Laisse les unités superposées se dégager, comme en jeu avant que le joueur ne donne l'ordre.
	for i in int(2.0 / TICK):
		_simulation.step(TICK)
	print("  info  avant l'ordre : %d paires d'unités en recouvrement" % _min_clearance().overlaps)
	var squads: Array[Squad] = _simulation.squads.duplicate()
	_move(squads, Vector3(0.0, 0.0, 80.0))
	print("  info  bloc de l'ordre de groupe : %.0f m de large" % _group_line_width(squads))
	await _run_until_idle(squads, false, "e2")


## Une escouade de Pisto-pois envoyée à travers un mur d'ennemis à l'arrêt : 21 Z-Mech
## tous les 1,9 m (0,3 m de passage, moins de la moitié du corps d'un Pisto-pois). Elle ne peut
## pas passer et doit s'arrêter proprement, en formation, devant le mur.
func _scenario_enemy_wall() -> void:
	for i in 21:
		_simulation.spawn_squad(_squad_data("z_mech"), 1, Vector3((i - 10) * 1.9, 0.0, 0.0), PI)
	var mover := _simulation.spawn_squad(_squad_data("peashooter"), 0, Vector3(0.0, 0.0, -14.0), 0.0)
	_move([mover], Vector3(0.0, 0.0, 14.0))
	await _run_until_idle([mover], false)
	_check(_last_stalled == 1, "blocage détecté : l'escouade s'est arrêtée d'elle-même")
	_check(mover.get_center().z < 0.0, "arrêt devant le mur (z = %.1f m ; mur en z = 0)" % mover.get_center().z)


func _group_line_width(squads: Array[Squad]) -> float:
	var lo := INF
	var hi := -INF
	for squad in squads:
		var target := (squad.order as MoveOrder).target
		lo = minf(lo, target.x)
		hi = maxf(hi, target.x)
	return hi - lo


## Une escouade de Zombies classiques envoyée exactement sur une escouade alliée à
## l'arrêt : les deux se superposent, s'arrêtent, et personne ne court sur place.
func _scenario_onto_idle() -> void:
	var idle := _simulation.spawn_squad(_squad_data("peashooter"), 0, Vector3.ZERO, 0.0)
	var mover := _simulation.spawn_squad(_squad_data("browncoat"), 0, Vector3(0.0, 0.0, -16.0), 0.0)
	_move([mover], idle.get_center())
	await _run_until_idle([mover], false, "", false)
	var offset := mover.get_center() - idle.get_center()
	offset.y = 0.0
	print("  info  centres des deux escouades à %.2f m l'un de l'autre" % offset.length())


# --- Déroulement et mesures --------------------------------------------------

## Nouvelle simulation vide (la précédente est libérée). `visual` : ajoute un décor et
## l'affichage des unités pour les captures.
func _reset(visual: bool = false) -> void:
	if _simulation != null:
		_simulation.queue_free()
		_orders.queue_free()
	if _world != null:
		_world.queue_free()
		_world = null
	_simulation = UnitSimulation.new()
	_simulation.set_physics_process(false)
	root.add_child(_simulation)
	_orders = OrderSystem.new()
	_orders.simulation = _simulation
	root.add_child(_orders)
	if visual:
		_build_world()


func _build_world() -> void:
	_world = Node3D.new()
	var environment := WorldEnvironment.new()
	environment.environment = Environment.new()
	environment.environment.background_mode = Environment.BG_COLOR
	environment.environment.background_color = Color(0.74, 0.84, 0.92)
	environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.environment.ambient_light_color = Color(0.7, 0.75, 0.8)
	_world.add_child(environment)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-55.0, 30.0, 0.0)
	_world.add_child(sun)
	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(600.0, 600.0)
	var ground_material := StandardMaterial3D.new()
	ground_material.albedo_color = Color(0.42, 0.55, 0.28)
	plane.material = ground_material
	ground.mesh = plane
	_world.add_child(ground)
	_camera = Camera3D.new()
	_camera.far = 2000.0
	_world.add_child(_camera)
	var selection := SelectionController.new()
	selection.simulation = _simulation
	_world.add_child(selection)
	var renderer := UnitRenderer.new()
	renderer.simulation = _simulation
	renderer.selection = selection
	_world.add_child(renderer)
	root.add_child(_world)
	_camera.make_current()


## Capture cadrée sur l'ensemble des unités (vue orthographique plongeante depuis le sud).
func _screenshot(name: String) -> void:
	if _world == null:
		return
	var lo := Vector3(INF, 0.0, INF)
	var hi := Vector3(-INF, 0.0, -INF)
	for unit in _simulation.units:
		lo = Vector3(minf(lo.x, unit.position.x), 0.0, minf(lo.z, unit.position.z))
		hi = Vector3(maxf(hi.x, unit.position.x), 0.0, maxf(hi.z, unit.position.z))
	var center := (lo + hi) * 0.5
	var aspect := root.get_visible_rect().size.aspect()
	_camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	_camera.size = maxf((hi.z - lo.z) * 0.9, (hi.x - lo.x) / aspect) + 6.0
	_camera.position = center + Vector3(0.0, 0.87, 0.5) * 300.0
	_camera.look_at(center)
	await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(_screenshot_dir.path_join(name + ".png"))
	print("  info  capture %s.png" % name)


## Escouades de troupes variées (rotation sur toutes les troupes), en grille centrée,
## orientées vers +Z.
func _spawn_grid(count: int, per_row: int, center: Vector3, spacing: float, team: int) -> Array[Squad]:
	var squads: Array[Squad] = []
	var positions := SquadLayout.camp_positions(count, center, -1.0, per_row, spacing, spacing, 0.0)
	for i in count:
		squads.append(_simulation.spawn_squad(_squad_data(ALL_SQUADS[i % ALL_SQUADS.size()]), team, positions[i], 0.0))
	return squads


func _move(squads: Array[Squad], target: Vector3) -> void:
	_orders.issue_move(squads, target)


## Avance la simulation jusqu'à ce que toutes les escouades aient fini leur ordre (ou
## jusqu'au délai), puis vérifie les critères communs sur toutes les escouades.
## `check_arrival` : les destinations sont libres, l'arrivée exacte est exigée.
## `shot_prefix` : captures au départ, en route et à l'arrivée (si le décor existe).
## `expect_reformed` : false si des escouades sont volontairement superposées (leurs
## emplacements se recouvrent, elles ne peuvent pas toutes se reformer exactement).
func _run_until_idle(movers: Array[Squad], check_arrival: bool, shot_prefix: String = "",
		expect_reformed: bool = true) -> void:
	var targets: Dictionary[Squad, Vector3] = {}
	var timeout := 0.0
	for squad in movers:
		var order := squad.order as MoveOrder
		targets[squad] = order.target
		var distance := squad.get_center().distance_to(order.target)
		timeout = maxf(timeout, distance / squad.get_move_speed() * TIME_FACTOR + TIME_MARGIN)

	if not shot_prefix.is_empty():
		await _screenshot(shot_prefix + "_1_depart")
	var started := Time.get_ticks_msec()
	var elapsed := 0.0
	var pending := movers.size()
	var travel_clearance := INF
	var ticks := 0
	var step_usec := 0
	var stalled: Dictionary[Squad, bool] = {}
	while elapsed < timeout:
		var t0 := Time.get_ticks_usec()
		_simulation.step(TICK)
		step_usec += Time.get_ticks_usec() - t0
		elapsed += TICK
		ticks += 1
		if ticks % 10 == 0:
			travel_clearance = minf(travel_clearance, _min_clearance().clearance)
		if not shot_prefix.is_empty() and ticks == int(MID_SHOT_TIME / TICK):
			await _screenshot(shot_prefix + "_2_en_route")
		for squad in movers:
			if squad.order is MoveOrder and (squad.order as MoveOrder).stalled:
				stalled[squad] = true
		pending = movers.filter(func(s: Squad) -> bool: return s.order != null).size()
		if pending == 0:
			break
		# Rend la main au moteur de temps en temps (fenêtre réactive, sortie console).
		if int(elapsed / TICK) % 600 == 0:
			await process_frame
	var wall := (Time.get_ticks_msec() - started) / 1000.0

	_check(pending == 0, "ordres terminés : %d/%d en %.1f s simulées (délai %.0f s ; %.1f s réelles, %d unités)"
			% [movers.size() - pending, movers.size(), elapsed, timeout, wall, _simulation.units.size()])
	print("  info  marge min entre unités pendant la marche : %.2f m" % travel_clearance)
	_last_stalled = stalled.size()
	print("  info  escouades arrêtées sur blocage : %d" % stalled.size())
	print("  info  tick moyen : %.2f ms (%d ticks, %d unités)" % [step_usec / 1000.0 / maxi(ticks, 1), ticks, _simulation.units.size()])
	if pending > 0:
		_report_stuck(movers)

	for i in int(SETTLE_TIME / TICK):
		_simulation.step(TICK)
	if not shot_prefix.is_empty():
		await _screenshot(shot_prefix + "_3_arrivee")

	var clearance := _min_clearance()
	_check(clearance.clearance >= -OVERLAP_TOLERANCE,
			"aucune superposition à l'arrêt (marge min %.3f m, %d paires en recouvrement)"
			% [clearance.clearance, clearance.overlaps])

	var running := 0
	var fastest := 0.0
	for unit in _simulation.units:
		var speed := Vector2(unit.velocity.x, unit.velocity.z).length()
		fastest = maxf(fastest, speed)
		if speed > REST_SPEED:
			running += 1
	_check(running == 0, "personne ne court dans le vide : %d unité(s) en mouvement (vitesse max %.2f m/s)"
			% [running, fastest])

	var unformed := 0
	var worst := 0.0
	for squad in _simulation.squads:
		var error := squad.get_formation_error()
		worst = maxf(worst, error)
		if error >= REST_FORMATION_ERROR:
			unformed += 1
	if expect_reformed:
		_check(unformed == 0, "formations reformées : %d/%d (écart max %.2f m)"
				% [_simulation.squads.size() - unformed, _simulation.squads.size(), worst])
	else:
		print("  info  formations reformées : %d/%d (superposition voulue)" % [_simulation.squads.size() - unformed, _simulation.squads.size()])

	if check_arrival:
		for squad in movers:
			var offset := squad.get_center() - targets[squad]
			offset.y = 0.0
			_check(offset.length() < POSITION_TOLERANCE,
					"escouade %d arrivée à destination (écart %.2f m)" % [squad.id + 1, offset.length()])


## Diagnostic des ordres non terminés.
func _report_stuck(movers: Array[Squad]) -> void:
	var shown := 0
	for squad in movers:
		var order := squad.order as MoveOrder
		if order == null or shown >= 6:
			continue
		shown += 1
		print("        escouade %d (%s) : phase %d, ancre à %.1f m du but, centre à %.1f m, écart formation %.2f m"
				% [squad.id + 1, squad.data.unit_data.id, order.phase, order.target.distance_to(squad.anchor),
				order.target.distance_to(squad.get_center()), squad.get_formation_error()])


## Plus petite marge entre deux unités (distance au sol moins la somme des rayons) et
## nombre de paires en recouvrement, via une grille pour rester rapide à 1 000 unités.
func _min_clearance() -> Dictionary:
	var units := _simulation.units
	var grid := SpatialHashGrid.new(4.0)
	for i in units.size():
		grid.insert(i, units[i].position)
	var best := INF
	var overlaps := 0
	for i in units.size():
		for j in grid.query(units[i].position, 4.0):
			if j <= i:
				continue
			var offset := units[i].position - units[j].position
			offset.y = 0.0
			var clearance := offset.length() - units[i].data.radius - units[j].data.radius
			best = minf(best, clearance)
			if clearance < -OVERLAP_TOLERANCE:
				overlaps += 1
	return {"clearance": best, "overlaps": overlaps}


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


# --- Utilitaires -------------------------------------------------------------

func _squad_data(id: String) -> SquadData:
	return load(SQUAD_DIR + id + "_squad.tres") as SquadData


func _check(condition: bool, label: String) -> void:
	_checks += 1
	print(("  OK    " if condition else "  ÉCHEC ") + label)
	if not condition:
		_failures.append(label)
